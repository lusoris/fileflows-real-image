<!-- markdownlint-disable MD024 -->
# Changelog

All notable changes to **FileFlows Real Image** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Comprehensive multi-AI contributor directives: [AGENTS.md](AGENTS.md), [CLAUDE.md](CLAUDE.md), [.windsurfrules](.windsurfrules), and [.cursor/rules/fileflows.mdc](.cursor/rules/fileflows.mdc).
- Automated linting and secret protection via [.pre-commit-config.yaml](.pre-commit-config.yaml), [.markdownlint.json](.markdownlint.json), [.codespellrc](.codespellrc), and [.gitleaks.toml](.gitleaks.toml).
- Developer convenience tooling: [Makefile](Makefile) and [pyproject.toml](pyproject.toml).
- Curated zero-shareware VS Code workspace configuration in [.vscode/](.vscode/).

### Changed
- Streamlined `:cuda` flavor to pure host-based NVIDIA driver injection (`libcuda`, NVENC, NVDEC) via NVIDIA Container Toolkit, cutting content size to 473 MB and virtual size to 1.65 GB (-72%).
- Upgraded `:cuda13` flavor to minimal cutting-edge NVIDIA CUDA 13.4 runtime with NVRTC and NPP video filters (`cuda-nvrtc-13-4`, `cuda-cudart-13-4`, `libnpp-13-4`), cutting virtual disk size to 2.33 GB (-54%).
- Tightened image virtual size gate assertion in tests to 3.5 GB.
- Improved branch-protection resilience in [.github/workflows/build-and-release.yml](.github/workflows/build-and-release.yml).

---

## [26.09.2-real.8] - 2026-09-09

### Added
- Dynamic Shields.io badge endpoints for content size, upstream version, and hardware flavors in `docs/badges/`.
- Multi-architecture container layer size calculation in release workflow.

---

## [26.09.2-real.7] - 2026-09-09

### Security
- Upgraded vulnerable and deprecated upstream NuGet assemblies across `/app`:
  - `Azure.Identity` upgraded to 1.21.0 (resolves CVE-2023-36414, CVE-2024-29992, CVE-2024-35255).
  - `Microsoft.Data.SqlClient` upgraded to 5.2.2 (resolves CVE-2024-0056).
  - `System.Drawing.Common` upgraded to 8.0.0 (resolves CVE-2021-24112).
- Automatic patching of assembly references across all `/app/**/*.deps.json` manifests.

---

## [26.09.2-real.6] - 2026-09-09

### Added
- Specialized vendor-optimized hardware acceleration image flavors:
  - `:intel` for Intel QuickSync & Arc GPUs (`intel-media-va-driver-non-free`, Level Zero, oneVPL, OpenCL ICD).
  - `:amd` for AMD Radeon RX 5000–8000 & Ryzen APUs (`mesa-libgallium` VA-API, RADV Vulkan).
  - Dedicated multi-flavor documentation in `docs/hardware-acceleration.md`.

---

## [26.09.2-real.1] - 2026-09-09

### Added
- Initial hardened multi-stage container build for FileFlows from upstream `revenz/fileflows:latest`.
- Zero base CVEs achieved via Canonical Rockcraft `pebble` daemon purge and rootfs layer squashing.
- Replaced `dotnet-sdk-10.0` with `aspnetcore-runtime-10.0` to eliminate 600 MB+ of SDK bloat.
- Replaced `-dev` compiler packages with dynamic shared libraries (`libavcodec62`, `libavformat62`, `libswscale9`).
- Instant boot (< 1s) with pre-baked hardware acceleration and neutralized runtime `apt-get` calls.
