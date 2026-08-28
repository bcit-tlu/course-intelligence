# Deployment

## Local Development

Use `docker compose up` to run the full stack locally:

- **API** — FastAPI on port 8000
- **Worker** — background job processor
- **Gateway** — LLM gateway on port 8100
- **Postgres** — database
- **Redis** — job queue
- **MinIO** — S3-compatible object storage
- **Studio** — Vite dev server on port 5173

## Kubernetes Deployment

Course Intelligence is deployed to Kubernetes using Helm charts in `charts/`.
The backend image (`course-intelligence-api`) backs three Deployments —
**api**, **worker**, and **gateway** — each overriding the container command
(`main.py {api,worker,gateway}`). The Studio workload (nginx) serves the SPA
and reverse-proxies `/api` to the backend Service.

```text
Ingress → studio (nginx) → api (:8000) → Postgres (CNPG + pgvector)
                               │  └─ enqueue → Redis → worker → llm-gateway (:8100)
                               └─ uploads → MinIO (S3)
```

### Helm Charts

| Chart | Directory | Components |
|-------|-----------|------------|
| `course-intelligence-backend` | `charts/backend/` | API, worker, gateway, Postgres, Redis, MinIO |
| `course-intelligence-studio` | `charts/studio/` | Studio (nginx) |

### Published Images

CI builds and pushes on every `main` push; release images are tagged `vX.Y.Z`
+ `latest` on git tags:

- `ghcr.io/bcit-tlu/course-intelligence/course-intelligence-api`
- `ghcr.io/bcit-tlu/course-intelligence/course-intelligence-studio`

### Deployment via Flux

Course Intelligence is deployed by [Flux](https://fluxcd.io) using `HelmRelease`
and `OCIRepository` manifests in the `flux-fleet` repo:

```
flux-fleet/apps/overlays/<latest|stable>/course-intelligence/
├── backend/values-<env>.yaml
└── studio/values-<env>.yaml
```

### Secrets

Create secrets out-of-band before installing:

```sh
kubectl create namespace course-intelligence

kubectl -n course-intelligence create secret generic course-intelligence-llm \
  --from-literal=ollama-api-key="$OLLAMA_API_KEY" \
  --from-literal=azure-openai-api-key=""
```

### Verification

```sh
# All pods Ready
kubectl -n course-intelligence get pods

# API health
kubectl -n course-intelligence port-forward svc/course-intelligence-backend 8000:8000 &
curl -s localhost:8000/health
```

### End-to-end Smoke Test

```sh
BASE=https://course-intelligence.<env>.ltc.bcit.ca

# 1. Enqueue a job
JOB=$(curl -s -X POST "$BASE/api/jobs" \
  -F "file=@module.pdf" \
  -F "learning_objectives=Recognize and manage sepsis" | jq -r .job_id)

# 2. Poll until completed
curl -s "$BASE/api/jobs/$JOB" | jq .status

# 3. Fetch results
curl -s "$BASE/api/jobs/$JOB/results" | jq '.elements[] | {topic, blooms_level}'
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | Postgres connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `S3_ENDPOINT_URL` | `http://localhost:9000` | S3-compatible endpoint |
| `S3_ACCESS_KEY` | `minioadmin` | S3 access key |
| `S3_SECRET_KEY` | `minioadmin` | S3 secret key |
| `S3_BUCKET` | `course-intelligence` | S3 bucket name |
| `LLM_PROVIDER` | `ollama` | LLM provider: `ollama`, `azure`, `litellm`, `mock` |
| `MOCK_LLM` | `false` | Use mock LLM for testing |
