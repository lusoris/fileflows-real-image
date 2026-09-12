# Security Policy

## Reporting a Vulnerability

**Please do not open a public issue for security problems.**

Use GitHub's private vulnerability-reporting flow:
`https://github.com/lusoris/fileflows-real-image/security/advisories/new`

If the issue is in upstream FileFlows application code (`FileFlows.Server`, `FileFlows.Agent`, etc.), report directly to the [upstream repository](https://github.com/revenz/FileFlows/issues).

Alternative channels:

- Email: `lusoris@pm.me` — PGP-encrypt sensitive material; request the public key via the same address.

Please include:

1. Affected image tag / commit SHA.
2. A minimal reproducer (`docker run` invocation, parameters, expected vs. actual behavior).
3. Assessment of impact (privilege escalation, remote code execution, container breakout).

## Scope

Security-sensitive surfaces in this project include:

- The multi-stage `Dockerfile` and rootfs squashing stages.
- Installed base packages, driver libraries, and hardware-acceleration runtimes.
- GitHub Actions automated build, push, and release pipelines.
- Container permission models and user execution (`PUID`/`PGID` handling in `docker-entrypoint.sh`).

## Base Image & Vulnerability Policy

This repository actively hardens the upstream container by:

- Updating base OS packages on build to latest Ubuntu 26.04 (Resolute) security errata.
- Completely removing unused third-party background daemons (such as Canonical's Rockcraft `pebble` binary) to eliminate upstream Go `stdlib` CVEs.
- Pruning cross-platform Windows (`win*`) and macOS (`osx*`) libraries from `/app/*/runtimes` that introduce known vulnerabilities on Linux hosts.
- Pre-installing required GPU drivers (`intel-media-va-driver-non-free`) to prevent runtime network downloads on startup.
