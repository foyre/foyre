# Security policy

## Reporting a vulnerability

**Please do not open public GitHub issues for security vulnerabilities.**

If you believe you've found a security issue in Foyre — in the application
itself, in its dependencies, or in how it handles credentials — please
report it privately by emailing:

**security@foyre.ai**

Include as much of the following as you can:

- A clear description of the issue and its potential impact.
- Steps to reproduce, including relevant versions, configuration, and a
  minimal proof-of-concept if possible.
- Your name or handle, and whether you want to be credited in the
  eventual advisory.

We'll acknowledge receipt within **3 business days**, and aim to send you
a more substantive response (including a proposed fix timeline or a
reason for classifying it as non-urgent) within **10 business days**.

Please do not publicly disclose the issue until we've had a reasonable
chance to investigate and ship a fix — typically no more than 90 days,
and usually much less for clearly-exploitable issues. We'll coordinate
any public disclosure with you.

## Scope

In scope:

- Authentication and session handling flaws.
- Authorization bypass between roles or between users.
- Leakage of secrets handled by Foyre — host-cluster kubeconfigs, user
  vcluster kubeconfigs, JWT secrets, password hashes.
- Injection flaws (SQLi, command injection via the `vcluster` shell-out,
  etc.).
- Storage or transmission of plaintext credentials that should be
  encrypted.
- Provisioning flaws that let a requester escape or affect the host
  cluster.

Out of scope:

- Issues in third-party dependencies that are better reported upstream;
  please open those with the dependency's maintainers. If the
  vulnerability meaningfully changes Foyre's posture, still let us know.
- Social engineering of maintainers or contributors.
- Denial-of-service via resource exhaustion on a single-user dev
  deployment.
- Missing security headers on the dev server (Vite / `uvicorn --reload`).
  Production deployments are expected to be fronted by a proper reverse
  proxy.

## Supported versions

Foyre is pre-1.0. During this period, security fixes are only applied to
the most recent release. Older versions are not backported.

When a 1.0 release is cut, this policy will be updated to specify which
major/minor lines receive backports.
