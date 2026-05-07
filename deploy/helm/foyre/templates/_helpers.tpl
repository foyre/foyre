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
Whether the chart should mount /data and persist the SQLite database.
True only when no other backend has been selected — i.e. SQLite is the
chosen backend.
*/}}
{{- define "foyre.usePersistence" -}}
{{- $url := .Values.database.url | default "" -}}
{{- $isSqliteUrl := hasPrefix "sqlite" $url -}}
{{- $isPostgresUrl := hasPrefix "postgres" $url -}}
{{- $hasExistingSecret := ne (.Values.database.existingSecret | default "") "" -}}
{{- $bundledPg := and .Values.postgresql .Values.postgresql.enabled -}}
{{- $externalPg := ne (.Values.database.postgres.host | default "") "" -}}
{{- $useSqlite := or (not $url) $isSqliteUrl -}}
{{- if and .Values.persistence.enabled $useSqlite (not $isPostgresUrl) (not $hasExistingSecret) (not $bundledPg) (not $externalPg) -}}
true
{{- end -}}
{{- end -}}

{{/*
Whether the chart should provision a PVC. Only when persistence is in use
AND no pre-existing claim was supplied.
*/}}
{{- define "foyre.shouldCreatePVC" -}}
{{- if and (eq (include "foyre.usePersistence" .) "true") (not .Values.persistence.existingClaim) -}}
true
{{- end -}}
{{- end -}}

{{/*
Compute the DATABASE_URL stored in the chart-managed Secret.

Precedence (first match wins):
  1. database.existingSecret    -> caller never reaches this helper
  2. database.url               -> used as-is
  3. postgresql.enabled         -> bundled Bitnami Postgres at <release>-postgresql:5432
  4. database.postgres.host set -> external postgresql+psycopg://user:pass@host:port/db[?sslmode=...]
  5. default                    -> sqlite:///<database.sqlite.path>
*/}}
{{- define "foyre.databaseUrl" -}}
{{- $url := .Values.database.url | default "" -}}
{{- $bundledPg := and .Values.postgresql .Values.postgresql.enabled -}}
{{- $externalPgHost := .Values.database.postgres.host | default "" -}}
{{- if $url -}}
{{- $url -}}
{{- else if $bundledPg -}}
{{- $auth := (.Values.postgresql.auth | default dict) -}}
{{- $user := ($auth.username | default "foyre") -}}
{{- $pass := ($auth.password | default "") -}}
{{- if not $pass -}}
{{- fail "postgresql.auth.password must be set when postgresql.enabled=true" -}}
{{- end -}}
{{- $db := ($auth.database | default "foyre") -}}
{{/* Bitnami chart fullname when included as a subchart aliased "postgresql". */}}
{{- $pgFull := default (printf "%s-postgresql" .Release.Name) (.Values.postgresql.fullnameOverride) -}}
{{- printf "postgresql+psycopg://%s:%s@%s:5432/%s" $user $pass $pgFull $db -}}
{{- else if $externalPgHost -}}
{{- $pg := .Values.database.postgres -}}
{{- $port := $pg.port | default 5432 -}}
{{- $db := $pg.database | default "foyre" -}}
{{- $user := $pg.user | default "foyre" -}}
{{- $pass := $pg.password | default "" -}}
{{- if not $pass -}}
{{- fail "database.postgres.password must be set when database.postgres.host is set" -}}
{{- end -}}
{{- $base := printf "postgresql+psycopg://%s:%s@%s:%v/%s" $user $pass $externalPgHost $port $db -}}
{{- if $pg.sslmode -}}
{{- printf "%s?sslmode=%s" $base $pg.sslmode -}}
{{- else -}}
{{- $base -}}
{{- end -}}
{{- else -}}
{{- $sqlite := .Values.database.sqlite | default dict -}}
{{- $path := $sqlite.path | default "/data/foyre.db" -}}
{{- printf "sqlite:///%s" $path -}}
{{- end -}}
{{- end -}}
