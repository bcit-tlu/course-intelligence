{{- define "course-intelligence-studio.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "course-intelligence-studio.fullname" -}}
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

{{- define "course-intelligence-studio.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ include "course-intelligence-studio.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "course-intelligence-studio.selectorLabels" -}}
app.kubernetes.io/name: {{ include "course-intelligence-studio.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "course-intelligence-studio.image" -}}
{{- printf "%s:%s" .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) -}}
{{- end -}}

{{/*
Cluster-internal backend URL. Prefers an explicit override, otherwise
builds the Service FQDN so kube-dns always resolves it (survives corporate
firewalls that block non-443 traffic on node IPs).
*/}}
{{- define "course-intelligence-studio.backendUrl" -}}
{{- if .Values.env.BACKEND_URL -}}
{{- .Values.env.BACKEND_URL -}}
{{- else -}}
{{- printf "http://%s.%s.svc.cluster.local:%d" .Values.backend.host (.Values.backend.namespace | default .Release.Namespace) (.Values.backend.port | int) -}}
{{- end -}}
{{- end -}}
