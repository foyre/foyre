{{/*
Expand the name of the chart.
*/}}
{{- define "foyre.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "foyre.fullname" -}}
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

{{/*
Chart label.
*/}}
{{- define "foyre.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels applied to every resource.
*/}}
{{- define "foyre.labels" -}}
helm.sh/chart: {{ include "foyre.chart" . }}
{{ include "foyre.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels.
*/}}
{{- define "foyre.selectorLabels" -}}
app.kubernetes.io/name: {{ include "foyre.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
ServiceAccount name to use.
*/}}
{{- define "foyre.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "foyre.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/*
Container image with chart-default tag fallback.
*/}}
{{- define "foyre.image" -}}
{{- $tag := default .Chart.AppVersion .Values.image.tag -}}
{{- printf "%s:%s" .Values.image.repository $tag -}}
{{- end -}}

{{/*
Name of the Secret holding APP_SECRET_KEY and JWT_SECRET.
Returns the user-provided existingSecret if set; otherwise the
chart-managed Secret name.
*/}}
{{- define "foyre.appSecretName" -}}
{{- if .Values.secrets.existingSecret -}}
{{- .Values.secrets.existingSecret -}}
{{- else -}}
{{- printf "%s-app" (include "foyre.fullname" .) -}}
{{- end -}}
{{- end -}}

{{/*
Name of the Secret holding the seed admin password.
*/}}
{{- define "foyre.seedSecretName" -}}
{{- printf "%s-seed" (include "foyre.fullname" .) -}}
{{- end -}}

{{/*
Name of the database Secret (only created if a database URL is provided
inline; if existingSecret is set we read from there).
*/}}
{{- define "foyre.dbSecretName" -}}
{{- if .Values.database.existingSecret -}}
{{- .Values.database.existingSecret -}}
{{- else -}}
{{- printf "%s-db" (include "foyre.fullname" .) -}}
{{- end -}}
{{- end -}}

{{/*
Name of the PVC.
*/}}
{{- define "foyre.pvcName" -}}
{{- if .Values.persistence.existingClaim -}}
{{- .Values.persistence.existingClaim -}}
{{- else -}}
{{- printf "%s-data" (include "foyre.fullname" .) -}}
{{- end -}}
{{- end -}}

{{/*
Whether the chart should provision a PVC. Only when persistence.enabled
AND no pre-existing claim was supplied.
*/}}
{{- define "foyre.shouldCreatePVC" -}}
{{- and .Values.persistence.enabled (not .Values.persistence.existingClaim) -}}
{{- end -}}
