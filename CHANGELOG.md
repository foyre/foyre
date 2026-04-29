# Changelog

All notable changes to Foyre will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Relicensed from the Business Source License 1.1 to the Apache License,
  Version 2.0. Foyre is now permissively open source — commercial use is
  permitted under the terms of Apache 2.0.

## [0.1.0] - 2026-04-23

Initial public release.

### Added
- Structured intake form for AI deployment requests with conditional
  fields, client-side validation, and draft / submit flow.
- Deterministic risk classification (low / medium / high / unknown) with
  human-readable reasons; rules live in `services/risk_service.py`.
- Workflow lifecycle: `draft → submitted → ready_for_review →
  under_review → approved | rejected`, enforced by a single transition
  table in `services/workflow_service.py`.
- Reviewer comments and an append-only history of lifecycle events
  (creation, edits, submissions, status changes, comments, validation
  environment events).
- Local username/password authentication with bcrypt hashing, JWT
  access tokens, and forced password rotation for temporary accounts.
- Pluggable authentication-provider interface — local provider only
  today; LDAP / AD / OIDC slots reserved.
- Role model: `requester`, `reviewer`, `architect`, `admin`. Admin can
  act on behalf of other users, recorded in the audit trail.
- Per-request validation environments via
  [vcluster](https://www.vcluster.com): isolated virtual clusters
  provisioned on a host Kubernetes cluster, with scoped kubeconfigs
  delivered to the requester through a once-shown download callout.
- Admin-managed host cluster configurations with kubeconfig encryption
  at rest (Fernet), in-app setup guide, and pre-save connection tests.
- Web UI: requests list with status filter pills and free-text search,
  request detail with role-aware actions, account page, and an admin
  section with horizontal tabs for Users and Validation environments.
- Foyre branding (logo, favicon, login page, navbar).

### Notes
- Licensed under the [Apache License, Version 2.0](./LICENSE).

[Unreleased]: https://github.com/zfeldstein/foyre/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/zfeldstein/foyre/releases/tag/v0.1.0
