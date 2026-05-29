"""Canonical default validation pipeline shipped with Foyre.

This is seeded into the `validation_pipelines` table on first run (see
`app.seed`). It mirrors the example in the feature brief: workload
inventory → kubernetes security → image scan, with sensible failure
policies (inventory warns, security/image-scan block on the serious
findings).

The YAML here is the user-facing source of truth; the parser
(`validation_pipeline_service`) normalizes it into the JSON the runner
consumes. We keep it as a literal string so the seeded pipeline's
`definition_yaml` reads exactly like something an admin would author.
"""
from __future__ import annotations

DEFAULT_PIPELINE_NAME = "default-ai-workload-validation"

DEFAULT_PIPELINE_YAML = """\
apiVersion: foyre.ai/v1alpha1
kind: ValidationPipeline
metadata:
  name: default-ai-workload-validation
  displayName: Default AI Workload Validation
  description: >-
    Default validation pipeline for AI workloads deployed in a Foyre
    validation environment. Collects a workload inventory, reviews
    Kubernetes security posture, and scans container images.
spec:
  failurePolicy: warn
  steps:
    - name: workload-inventory
      type: builtin.workload_inventory
      displayName: Workload Inventory
      description: Enumerate deployed resources and collect non-secret metadata.
      required: true
      failurePolicy: warn
      timeoutSeconds: 120
      config:
        includeNamespaces:
          - "*"
        excludeNamespaces:
          - kube-system

    - name: kubernetes-security
      type: builtin.kubernetes_security
      displayName: Kubernetes Security Review
      description: Flag risky Kubernetes configuration in deployed workloads.
      required: true
      failurePolicy: block
      dependsOn:
        - workload-inventory
      timeoutSeconds: 120
      config:
        denyPrivilegedContainers: true
        warnIfRunAsRoot: true
        warnIfMissingResourceLimits: true
        warnIfHostPathMounts: true
        warnIfHostNetwork: true

    - name: image-scan
      type: builtin.image_scan
      displayName: Container Image Scan
      description: Scan discovered container images for known vulnerabilities.
      required: true
      failurePolicy: block
      dependsOn:
        - workload-inventory
      timeoutSeconds: 900
      config:
        scanner: trivy
        failOnCritical: true
        warnOnHigh: true
        ignoreUnfixed: false
"""
