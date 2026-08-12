# Course Intelligence — Kubernetes Deployment Runbook

This document covers installing, verifying, upgrading, and rolling back Course
Intelligence on a Kubernetes cluster using the Helm charts in `charts/`. For local
development use `docker compose up` instead.

> ### ⚠️ Breaking change — charts, images, namespace, and identifiers were renamed
>
> Charts, image names, Kubernetes resource names, namespace, secrets, and ingress
> hostnames moved from `dialog-*` to `course-intelligence-*`. Because
> `app.kubernetes.io/name` is part of each Deployment's **immutable**
> `spec.selector`, an in-place `helm upgrade` will **fail** — the existing
> Deployments must be deleted and recreated.
>
> Two changes must land together, or Studio cannot reach the API:
>
> 1. **This repo** — chart directory `charts/frontend` → `charts/studio`; charts
>    renamed to `course-intelligence-backend` / `course-intelligence-studio`;
>    images renamed to `course-intelligence-api` / `course-intelligence-studio`;
>    Postgres credentials renamed to `course_intelligence`.
> 2. **`flux-fleet`** — the overlays must set
>    `fullnameOverride: course-intelligence-backend` and
>    `course-intelligence-studio`, and point `OCIRepository` at the renamed
>    charts. The studio chart's default `backend.host` is
>    `course-intelligence-backend`, which only resolves if the backend release's
>    Service carries that exact name.
>
> Migration: since this is a beta application with downtime/data loss acceptable,
> the cutover is a clean rebuild — delete the old namespace, create the new one,
> recreate secrets, and let Flux reconcile. See
> [architecture.md](architecture.md#legacy-identifiers) for the full decision record.

## Architecture

One backend image (`course-intelligence-api`) backs three Deployments — **api**, **worker**, and
**gateway** — each overriding the container `command` (`main.py {api,worker,gateway}`).
The Studio workload (nginx) serves the SPA and reverse-proxies `/api` to the
backend Service, with `BACKEND_URL` injected at container start via `envsubst`.

```text
Ingress → studio (nginx) → api (:8000) → Postgres (CNPG + pgvector)
                               │  └─ enqueue → Redis → worker → llm-gateway (:8100)
                               └─ uploads → MinIO (S3)
```

## Prerequisites

Cluster-admin, once per cluster:

- **CloudNative-PG (CNPG) operator** ≥ 1.29 — required for the Postgres `Cluster`.
  - pgvector via image-volume extensions additionally needs **PostgreSQL 18+** and
    **Kubernetes 1.33+** with the `ImageVolume` feature. On older clusters set
    `postgres.pgvector.enabled=false` and use a custom operand image.
- **Ingress controller** (e.g. ingress-nginx) — for the Studio Ingress.
- **metrics-server** — only if you enable the worker HPA (`worker.autoscaling.enabled=true`).

Tooling: `helm` ≥ 3.12, `kubectl` matching the cluster.

## Published images

CI (`.github/workflows/ci.yaml`) builds and pushes on every `main` push and git tag:

- `ghcr.io/bcit-tlu/course-intelligence/course-intelligence-api`
- `ghcr.io/bcit-tlu/course-intelligence/course-intelligence-studio`

Tags: `sha-<shortsha>` on every build; `vX.Y.Z` + `latest` on git tags. The Flux fleet
overlay pins chart versions via `OCIRepository` semver constraints (see the
`flux-fleet` repo, `apps/overlays/latest/course-intelligence/`).

## Secrets (out-of-band, pre-Vault)

Create secrets before installing so nothing sensitive lives in git or images. The charts
reference these by name; every reference also supports an `existingSecret` value so a later
migration to Vault (Agent injector / External Secrets Operator) needs no template change.

```sh
kubectl create namespace course-intelligence

# LLM credentials — keys are pinned so ollama/azure are interchangeable.
# (Ollama Cloud may need no key; create with empty values if so.)
kubectl -n course-intelligence create secret generic course-intelligence-llm \
  --from-literal=ollama-api-key="$OLLAMA_API_KEY" \
  --from-literal=azure-openai-api-key=""

# Object storage (only when pointing at external S3, i.e. minio.enabled=false;
# in-cluster MinIO creates its own Secret). Keys: root-user / root-password.
# kubectl -n course-intelligence create secret generic course-intelligence-s3 \
#   --from-literal=root-user=... --from-literal=root-password=...
```

Then reference them in the Flux fleet overlay: `llm.existingSecret: course-intelligence-llm`
(already set in `flux-fleet/apps/overlays/latest/course-intelligence/backend/values-latest.yaml`),
and `minio.existingSecret: course-intelligence-s3` for the external-S3 path.

## Deploy (via Flux)

Course Intelligence is deployed to the cluster by [Flux](https://fluxcd.io) using `HelmRelease` and
`OCIRepository` manifests in the
[`flux-fleet`](https://github.com/bcit-tlu/flux-fleet) repo:

```
flux-fleet/apps/overlays/<latest|stable>/course-intelligence/
├── kustomization.yaml
├── backend/values-<env>.yaml    # HelmRelease + OCIRepository for the backend chart
└── studio/values-<env>.yaml     # HelmRelease + OCIRepository for the studio chart
```

There are **two** environments — `latest` and `stable` — and both must be updated
together for any chart rename.

Flux watches the OCI chart repository at
`oci://ghcr.io/bcit-tlu/course-intelligence/charts/course-intelligence-backend`
(and `-studio`), pulls the latest semver-matching version, and applies the values
from the overlay.

### Making changes

1. **Values changes** — edit the overlay in `flux-fleet` and push. Flux reconciles
   automatically on the next sync interval.
2. **New image** — CI builds and publishes the chart on every `main` push and git tag.
   Flux picks up the new chart version via the `OCIRepository` semver constraint
   (`>= 0.0.0-0` for `latest`).

> **Single name family.** The `flux-fleet` overlays set `RELEASE_NAME:
> course-intelligence`, so **Kubernetes workload names**, **Helm release names**,
> and **Flux CR names** are all `course-intelligence-backend` and
> `course-intelligence-studio`.
>
> So: `kubectl logs deploy/course-intelligence-backend` and
> `flux reconcile helmrelease course-intelligence-backend`.

## Verify

```sh
# All pods Ready (api, worker, gateway, redis, minio, postgres, studio).
kubectl -n course-intelligence get pods

# Migration ran: the api pod's `migrate` initContainer applied Alembic head.
kubectl -n course-intelligence logs deploy/course-intelligence-backend -c migrate

# pgvector enabled in the app DB.
kubectl -n course-intelligence exec -it course-intelligence-backend-db-1 -- psql -U course_intelligence -d course_intelligence -c '\dx'
#   → the `vector` extension is listed.

# uploads bucket created by the post-install Job.
kubectl -n course-intelligence get job -l app.kubernetes.io/component=minio-init

# API health through the Service.
kubectl -n course-intelligence port-forward svc/course-intelligence-backend 8000:8000 &
curl -s localhost:8000/health   # → {"status":"ok",...}
```

## End-to-end smoke test

Reach the app via the Ingress host (or `kubectl port-forward svc/course-intelligence-studio
8080:80`), then exercise the async flow (`course_intelligence/api.py`):

```sh
BASE=https://course-intelligence.<env>.ltc.bcit.ca   # e.g. course-intelligence.staging.ltc.bcit.ca

# 1. Enqueue a job (multipart upload + optional objectives).
JOB=$(curl -s -X POST "$BASE/api/jobs" \
  -F "file=@docs/nursing_sepsis_learning_module.pdf" \
  -F "learning_objectives=Recognize and manage sepsis" | jq -r .job_id)

# 2. Poll until completed (worker dequeues from Redis, runs the graph).
curl -s "$BASE/api/jobs/$JOB" | jq .status      # queued → processing → completed

# 3. Fetch results (topics + Bloom's levels).
curl -s "$BASE/api/jobs/$JOB/results" | jq '.elements[] | {topic, blooms_level}'
```

Confirm in the UI: topics render with Bloom's badges. Then restart pods
(`kubectl -n course-intelligence rollout restart deploy/course-intelligence-backend`) to prove migrations are
idempotent and no secret is baked into the image.

## Upgrade

Push changes to the `flux-fleet` overlay. Flux reconciles on the next sync interval,
or force a reconciliation:

```sh
flux reconcile helmrelease course-intelligence-backend -n course-intelligence
flux reconcile helmrelease course-intelligence-studio -n course-intelligence
```

- The api `migrate` initContainer re-runs `alembic upgrade head` on every rollout — idempotent.
- Changing the Studio nginx template rolls the pods automatically (a `checksum/config`
  annotation on the Deployment changes with the ConfigMap).

## Rollback

Revert the commit in the `flux-fleet` repo — Flux will reconcile back to the previous
chart version. For immediate rollback without waiting for Git:

```sh
flux suspend helmrelease course-intelligence-backend -n course-intelligence
helm rollback course-intelligence-backend <REVISION> -n course-intelligence
flux resume helmrelease course-intelligence-backend -n course-intelligence
```

> **Schema note:** `helm rollback` reverts Kubernetes objects, not database schema. If a
> release included a destructive Alembic migration, roll the DB back separately
> (`alembic downgrade`) — application-level, out of Helm's scope.

## Production hardening (future)

- **Secrets → Vault:** swap the out-of-band Secrets for Vault-populated ones via the same
  `*.existingSecret` values — no template changes required.
- **Worker scaling:** the CPU/memory HPA (`worker.autoscaling.enabled=true`) needs
  metrics-server; for queue-depth-aware scaling on the Redis backlog, prefer KEDA.
- **External managed services:** set `postgres.enabled=false` + `postgres.uri`,
  `redis.enabled=false` + `redis.url`, and/or `minio.enabled=false` + `minio.endpointUrl`
  to use managed Postgres/Redis/S3 instead of the in-cluster deployments.
- **LLM gateway routing (Option B):** route all LLM calls through the gateway so only the
  gateway holds credentials.
