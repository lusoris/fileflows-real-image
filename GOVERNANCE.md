# Governance

## Model

**FileFlows Real Image** operates under a **maintainer-led governance model**. Maintainers hold merge rights to the repository; the project lead coordinates the roadmap, releases, and architectural decisions.

## Decision Making

- **Code Changes**: All changes must pass CI quality gates (Hadolint, Yamllint, ShellCheck, Pytest assertion suite, Dive layer efficiency, and Trivy security scans).
- **Architectural Invariants**: Any proposed change affecting the core invariants defined in [AGENTS.md](AGENTS.md) (such as base OS, zero-CVE policy, flavor definitions, or SDK elimination) requires explicit review and documentation synchronization.
- **Upstream Synchronization**: Releases track upstream `revenz/fileflows:latest` digests and publish monotonic `-real.<N>` tags.

## Releases

Releases are built, verified, and published automatically via GitHub Actions upon upstream digest updates or pushes to `main`. Every release publishes multi-arch images to GitHub Container Registry (GHCR) and generates release notes and provenance data.

## Security

Security vulnerabilities must be reported through the coordinated disclosure process outlined in [SECURITY.md](SECURITY.md).
