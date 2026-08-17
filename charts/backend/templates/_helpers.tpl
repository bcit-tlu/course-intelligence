{{- define "course-intelligence-backend.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "course-intelligence-backend.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "course-intelligence-backend.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ include "course-intelligence-backend.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "course-intelligence-backend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "course-intelligence-backend.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Fully-qualified container image reference for the backend image.
One image backs all three roles (api / worker / gateway); the role is
selected by the container command in each Deployment.
*/}}
{{- define "course-intelligence-backend.image" -}}
{{- printf "%s:%s" .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) -}}
{{- end -}}

{{/*
Redis connection URL. When the in-cluster Redis is enabled, build the URL
from its Service; otherwise fall back to the externally-provided redis.url.
*/}}
{{- define "course-intelligence-backend.redisUrl" -}}
{{- if .Values.redis.enabled -}}
{{- printf "redis://%s-redis:6379/0" (include "course-intelligence-backend.fullname" .) -}}
{{- else -}}
{{- .Values.redis.url -}}
{{- end -}}
{{- end -}}

{{/*
Name of the Secret holding MinIO/S3 root credentials (keys: root-user,
root-password). Prefers an existing Secret when provided.
*/}}
{{- define "course-intelligence-backend.minioSecretName" -}}
{{- .Values.minio.existingSecret | default (printf "%s-minio" (include "course-intelligence-backend.fullname" .)) -}}
{{- end -}}

{{/*
Name of the Secret holding LLM credentials (keys: api-key,
azure-openai-api-key). Prefers an existing Secret when provided.
*/}}
{{- define "course-intelligence-backend.llmSecretName" -}}
{{- .Values.llm.existingSecret | default (printf "%s-llm" (include "course-intelligence-backend.fullname" .)) -}}
{{- end -}}

{{/*
Name of the Secret holding the Postgres connection URI (key: uri).
Prefers an existing Secret when provided; falls back to the chart-managed
<fullname>-db Secret created by postgres-cluster.yaml.
*/}}
{{- define "course-intelligence-backend.postgresSecretName" -}}
{{- .Values.postgres.existingSecret | default (printf "%s-db" (include "course-intelligence-backend.fullname" .)) -}}
{{- end -}}

{{/*
S3 endpoint URL. Uses the in-cluster MinIO Service when enabled, otherwise
the externally-provided endpoint.
*/}}
{{- define "course-intelligence-backend.s3EndpointUrl" -}}
{{- if .Values.minio.enabled -}}
{{- printf "http://%s-minio:9000" (include "course-intelligence-backend.fullname" .) -}}
{{- else -}}
{{- .Values.minio.endpointUrl -}}
{{- end -}}
{{- end -}}

{{/*
Core infra env shared by the api and worker roles: DB, Redis, and S3
credentials. DATABASE_URL comes from the CNPG Secret when Postgres is
in-cluster, otherwise from the external postgres.uri value.
*/}}
{{- define "course-intelligence-backend.coreEnv" -}}
- name: DATABASE_URL
{{- if or .Values.postgres.enabled .Values.postgres.existingSecret }}
  valueFrom:
    secretKeyRef:
      name: {{ include "course-intelligence-backend.postgresSecretName" . }}
      key: uri
{{- else }}
  value: {{ .Values.postgres.uri | quote }}
{{- end }}
- name: REDIS_URL
  value: {{ include "course-intelligence-backend.redisUrl" . | quote }}
- name: S3_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "course-intelligence-backend.minioSecretName" . }}
      key: root-user
- name: S3_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "course-intelligence-backend.minioSecretName" . }}
      key: root-password
{{- end -}}

{{/*
LLM credential env for the roles that call the provider directly.
Option A (see plans/step-08): mounted on the worker and gateway, NOT the api.
*/}}
{{- define "course-intelligence-backend.llmCredsEnv" -}}
- name: OLLAMA_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "course-intelligence-backend.llmSecretName" . }}
      key: api-key
- name: AZURE_OPENAI_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "course-intelligence-backend.llmSecretName" . }}
      key: azure-openai-api-key
{{- end -}}
