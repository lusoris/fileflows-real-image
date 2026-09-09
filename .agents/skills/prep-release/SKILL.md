---
name: prep-release
description: Prepare a release, update CHANGELOG.md, calculate image sizes, verify quality gates, and validate release tags.
---

# /prep-release

Prepares and validates a release of FileFlows Real Image before tagging and automated GHCR publication.

## Invocation

```bash
/prep-release
```

## Release Checklist

1. **Working Tree Cleanliness**:
   - Verify `git status` has no untracked or uncommitted changes.
2. **Quality Gates**:
   - Run full linter suite: `make lint` (Hadolint, Yamllint, ShellCheck).
   - Run documentation integrity tests: `make test-docs`.
   - Run pre-commit hooks: `pre-commit run --all-files`.
3. **Changelog Validation**:
   - Ensure changes in the release are summarized under a version heading in [CHANGELOG.md](../../../CHANGELOG.md).
   - Follow [Keep a Changelog](https://keepachangelog.com/) standards.
4. **Docs & Code Synchrony**:
   - Verify all table sizes in [README.md](../../../README.md), [AGENTS.md](../../../AGENTS.md), and [docs/hardware-acceleration.md](../../../docs/hardware-acceleration.md) match the built image sizes.
5. **Tag Convention**:
   - Pushes to `main` with monotonic upstream-tracking tags in format:
     `v<upstream_version>-real.<iteration>` (e.g. `v26.09.2-real.9`).
