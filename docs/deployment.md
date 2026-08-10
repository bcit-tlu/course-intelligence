# Dialog — Kubernetes Deployment Runbook

This document covers installing, verifying, upgrading, and rolling back Dialog on a
Kubernetes cluster using the Helm charts in `charts/`. For local development use
`docker compose up` instead.

## Architecture

One backend image (`dialog-api`) backs three Deployments — **api**, **worker**, and
**gateway** — each overriding the container `command` (`main.py {api,worker,gateway}`).
The **frontend** (nginx) serves the SPA and reverse-proxies `/api` to the backend Service,
with `BACKEND_URL` injected at container start via `envsubst`.

```text
Ingress → frontend (nginx) → api (:8000) → Postgres (CNPG + pgvector)
                                 │  └─ enqueue → Redis → worker → llm-gateway (:8100)
                                 └─ uploads → MinIO (S3)
```

## Prerequisites

Cluster-admin, once per cluster:

- **CloudNative-PG (CNPG) operator** ≥ 1.29 — required for the Postgres `Cluster`.
  - pgvector via image-volume extensions additionally needs **PostgreSQL 18+** and
    **Kubernetes 1.33+** with the `ImageVolume` feature. On older clusters set
    `postgres.pgvector.enabled=false` and use a custom operand image.
- **Ingress controller** (e.g. ingress-nginx) — for the frontend Ingress.
- **metrics-server** — only if you enable the worker HPA (`worker.autoscaling.enabled=true`).

Tooling: `helm` ≥ 3.12, `kubectl` matching the cluster.

## Published images

CI (`.github/workflows/build-images.yml`) builds and pushes on every `main` push and git tag:

- `ghcr.io/bcit-tlu/dialog/dialog-api`
- `ghcr.io/bcit-tlu/dialog/dialog-frontend`

Tags: `sha-<shortsha>` on every build; `vX.Y.Z` + `latest` on git tags. The Flux fleet
overlay pins chart versions via `OCIRepository` semver constraints (see the
`flux-fleet` repo, `apps/overlays/latest/dialog/`).

## Secrets (out-of-band, pre-Vault)

Create secrets before installing so nothing sensitive lives in git or images. The charts
reference these by name; every reference also supports an `existingSecret` value so a later
migration to Vault (Agent injector / External Secrets Operator) needs no template change.

```sh
kubectl create namespace dialog

# LLM credentials — keys are pinned so ollama/azure are interchangeable.
# (Ollama Cloud may need no key; create with empty values if so.)
kubectl -n dialog create secret generic dialog-llm \
  --from-literal=ollama-api-key="$OLLAMA_API_KEY" \
  --from-literal=azure-openai-api-key=""

# Object storage (only when pointing at external S3, i.e. minio.enabled=false;
# in-cluster MinIO creates its own Secret). Keys: root-user / root-password.
# kubectl -n dialog create secret generic dialog-s3 \
#   --from-literal=root-user=... --from-literal=root-password=...
```

Then reference them in the Flux fleet overlay: `llm.existingSecret: dialog-llm`
(already set in `flux-fleet/apps/overlays/latest/dialog/backend/values-latest.yaml`),
and `minio.existingSecret: dialog-s3` for the external-S3 path.

## Deploy (via Flux)

Dialog is deployed to the cluster by [Flux](https://fluxcd.io) using `HelmRelease` and
`OCIRepository` manifests in the
[`flux-fleet`](https://github.com/bcit-tlu/flux-fleet) repo:

```
flux-fleet/apps/overlays/latest/dialog/
├── kustomization.yaml
├── backend/values-latest.yaml    # HelmRelease + OCIRepository for the backend chart
└── frontend/values-latest.yaml   # HelmRelease + OCIRepository for the frontend chart
```

Flux watches the OCI chart repository at
`oci://ghcr.io/bcit-tlu/dialog/charts/<release>-backend` (and `-frontend`), pulls the
latest semver-matching version, and applies the values from the overlay.

### Making changes

1. **Values changes** — edit the overlay in `flux-fleet` and push. Flux reconciles
   automatically on the next sync interval.
2. **New image** — CI builds and publishes the chart on every `main` push and git tag.
   Flux picks up the new chart version via the `OCIRepository` semver constraint
   (`>= 0.0.0-0` for `latest`).

> **Service names:** the overlays set `fullnameOverride: dialog-backend` and
> `dialog-frontend`, so the Service names are `dialog-backend` and `dialog-frontend`
> respectively (no release-name prefix).

## Verify

```sh
# All pods Ready (api, worker, gateway, redis, minio, postgres, frontend).
kubectl -n dialog get pods

# Migration ran: the api pod's `migrate` initContainer applied Alembic head.
kubectl -n dialog logs deploy/dialog-backend -c migrate

# pgvector enabled in the app DB.
kubectl -n dialog exec -it dialog-backend-db-1 -- psql -U dialog -d dialog -c '\dx'
#   → the `vector` extension is listed.

# uploads bucket created by the post-install Job.
kubectl -n dialog get job -l app.kubernetes.io/component=minio-init

# API health through the Service.
kubectl -n dialog port-forward svc/dialog-backend 8000:8000 &
curl -s localhost:8000/health   # → {"status":"ok",...}
```

## End-to-end smoke test

Reach the app via the Ingress host (or `kubectl port-forward svc/dialog-frontend
8080:80`), then exercise the async flow (`dialog/api.py`):

```sh
BASE=https://dialog.<env>.ltc.bcit.ca   # e.g. dialog.staging.ltc.bcit.ca

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
(`kubectl -n dialog rollout restart deploy/dialog-backend`) to prove migrations are
idempotent and no secret is baked into the image.

## Upgrade

Push changes to the `flux-fleet` overlay. Flux reconciles on the next sync interval,
or force a reconciliation:

```sh
flux reconcile helmrelease dialog-backend -n dialog
flux reconcile helmrelease dialog-frontend -n dialog
```

- The api `migrate` initContainer re-runs `alembic upgrade head` on every rollout — idempotent.
- Changing the frontend nginx template rolls the pods automatically (a `checksum/config`
  annotation on the Deployment changes with the ConfigMap).

## Rollback

Revert the commit in the `flux-fleet` repo — Flux will reconcile back to the previous
chart version. For immediate rollback without waiting for Git:

```sh
flux suspend helmrelease dialog-backend -n dialog
helm rollback dialog-backend <REVISION> -n dialog
flux resume helmrelease dialog-backend -n dialog
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
