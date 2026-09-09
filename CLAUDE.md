<!-- markdownlint-disable MD013 -->
# Claude Code Guide — FileFlows Real Image

> Claude Code-specific operating guide. For comprehensive cross-tool conventions and architectural invariants, read [AGENTS.md](AGENTS.md) first; this file extends it.

---

## 1. What This Project Is

A hardened, minimal, multi-stage OCI container build system for [FileFlows](https://fileflows.com) that extracts assets directly from upstream `revenz/fileflows:latest`, strips legacy bloat, eliminates base vulnerabilities, and bakes vendor hardware drivers at build time across 5 distinct flavors (`all`, `intel`, `amd`, `cuda`, `cuda13`).

---

## 2. Fast Command Reference

```bash
# Development & Builds via Makefile
make build               # Build universal default flavor (:latest)
make build-intel         # Build Intel QuickSync & Arc flavor
make build-amd           # Build AMD Radeon & Ryzen APU flavor
make build-cuda          # Build host-based NVIDIA flavor
make build-cuda13        # Build minimal CUDA 13.4 runtime flavor
make build-all           # Build all 5 flavors locally

# Testing & Quality Gates
make test-docs           # Run doc consistency & link assertions (< 0.1s)
make test                # Run full pytest suite against local image
make lint                # Run Hadolint, Yamllint, and ShellCheck

# Documentation
make docs-serve          # Local MkDocs preview server on http://127.0.0.1:8000
make docs-build          # Build MkDocs site with strict validation
```

---

## 3. Modular Agent Skills & Subagents

Standardized skills are maintained in `.agents/skills/` (mirrored to `.claude/skills/`):
- `/build-flavor [flavor]`: Build target image with size gating.
- `/test-image [tag]`: Run full container assertion and runtime smoke tests.
- `/lint-all [--fix]`: Run Hadolint, Yamllint, ShellCheck, pre-commit.
- `/sync-upstream`: Query upstream Docker Hub digest and bump version.
- `/security-audit`: Run Trivy scan and NuGet vulnerability checks.
- `/prep-release`: Prepare changelog, verify quality gates, and validate tags.

Review agents in `.claude/agents/`:
- `container-reviewer`: Validates Dockerfile changes against invariants and layer squashing.
- `docs-reviewer`: Validates markdown links, anchors, and table metrics.

---

## 4. Strict Prohibitions ("Don't")

1. **Don't install .NET SDK**: Never install `dotnet-sdk-*`. Always use `aspnetcore-runtime-10.0`.
2. **Don't add `-dev` packages**: Production stages must strictly use shared runtime libraries (`libavcodec62`, `libavformat62`, `libswscale9`, `libssl3`, `libicu78`).
3. **Don't bloat CUDA images**:
   - `:cuda` relies on host driver injection (`NVIDIA_DRIVER_CAPABILITIES=compute,video,utility`).
   - `:cuda13` installs only `cuda-nvrtc-13-4`, `cuda-cudart-13-4`, and `libnpp-13-4`. Never install `libcublas`, `libcusolver`, `libcusparse`, `libcufft`, `libcurand`, or `cuda-compat`.
4. **Don't install ROCm**: AMD hardware transcoding uses Mesa Gallium VA-API and Vulkan Video. Never install ROCm compute SDKs.
5. **Don't let Dockerfiles drift**: [Dockerfile](Dockerfile) and [Dockerfile.optimized](Dockerfile.optimized) must remain 100% byte-identical.
6. **Don't commit broken docs**: Every change to flavors, sizes, or Compose configs must be synchronized across [README.md](README.md), [docs/](docs/), and [docker-compose.yml](docker-compose.yml). Run `make test-docs` before every commit.
7. **Don't violate NASA/JPL Power of 10 rules**: Follow [docs/principles.md](docs/principles.md). Keep functions <= 60 lines, maintain assertion density >= 2.0, and check every return value.

---

## 5. Verification Checklist Before Handoff

- [ ] `make test` and `make coverage` pass cleanly with >= 95% coverage and assertion density >= 2.0.
- [ ] `make lint` (Hadolint, Yamllint, ShellCheck) passes with 0 warnings.
- [ ] `Dockerfile` and `Dockerfile.optimized` are verified identical via `diff -u`.
- [ ] Any modified markdown conforms to `.markdownlint.json`.
- [ ] All commit messages and documentation are in clear, neutral English.
