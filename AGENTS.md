<!-- markdownlint-disable MD013 -->
# AGENTS.md — Agent & Contributor Directives

> Authoritative operating guide for all autonomous engineering agents (Antigravity, Cursor, Claude Code, Copilot, Aider, Codex, Windsurf) and human contributors in this repository.

---

## 🌟 TOP-PRIORITY GLOBAL RULES

These rules apply unconditionally to all agents, all tools, and all commits:

1. **Declarative Source of Truth**:
   All container definitions, configurations, and CI pipelines live declaratively in this repository. Never assume or hand-mutate external state.
2. **Preserve Architectural Invariants**:
   Every invariant defined in Section 2 must be maintained across all modifications. If an edit risks violating an invariant, stop, verify, and resolve the invariant first.
3. **Docs & Code Synchrony**:
   Every user-discoverable change (new flavor, configuration flag, environment variable, or dependency bump) must be reflected in the documentation ([README.md](README.md) and [docs/](docs/)) in the **exact same commit**.
4. **All Documentation in English**:
   All commit messages, code comments, documentation, and agent reports must be written in a neutral, professional English register.

---

## 1. Mission & Purpose

`fileflows-real-image` produces clean, hardened, production-ready multi-stage OCI container images for [FileFlows](https://fileflows.com) directly from the bloated upstream release (`revenz/fileflows:latest`).

It achieves:
- **Zero Base CVEs**: 100% elimination of base-image vulnerabilities (including the Canonical Rockcraft `pebble` Go stdlib CVEs).
- **Instant Boot (< 1s)**: Hardware acceleration drivers are baked in at build time; runtime `apt-get` calls in entrypoints are neutralized.
- **Slashed Footprint**: Image content size drops from 999 MB to **470–720 MB**; virtual disk usage is cut by **45–72%**.
- **Specialized Hardware Flavors**: Individual vendor-optimized flavors for Intel, AMD, and NVIDIA eliminate competing driver bloat.

---

## 2. Architectural Invariants

1. **Self-Contained Builds**:
   - The [Dockerfile](Dockerfile) must NEVER rely on local extracted files (`app/`, `docker-bin/`, etc.) or host-side build scripts.
   - All upstream assets must be extracted dynamically via `COPY --from=upstream` or multi-stage pipelines.
2. **Zero Base CVEs**:
   - The production images must maintain zero Critical/High vulnerabilities.
   - The Canonical Rockcraft `pebble` binary and directories (`/usr/bin/pebble`, `/var/lib/pebble`, `/etc/pebble`) must be purged, and layer history flattened via `FROM scratch COPY --from=base-selected / /`.
3. **No .NET SDK Bloat**:
   - Never install `dotnet-sdk-*`. Always use `aspnetcore-runtime-10.0` (Ubuntu 26.04+). Dynamic Roslyn compilation in FileFlows executes in-memory on the runtime.
4. **No Dev Compilers or Header Packages**:
   - Never install `-dev` packages in production stages.
   - Use lean shared libraries (`libavcodec62`, `libavformat62`, `libswscale9`, `libicu78`, `libssl3`).
5. **Instant Startup**:
   - Pre-install vendor hardware drivers (`intel-media-va-driver-non-free`, etc.) at build time so `docker-entrypoint.sh` never triggers `apt-get update` on container start. Neutralize runtime apt calls via `sed`.
6. **Multi-Arch Support**:
   - Both `linux/amd64` and `linux/arm64` must build cleanly for universal (`all`) and AMD flavors.
   - Intel- and CUDA-specific packages must be conditionally scoped to `amd64`.
7. **Dead Runtime Stripping**:
   - Prune dead Windows and macOS runtime directories (`runtimes/win*`, `runtimes/osx*`) from `/app` in Stage 1.
8. **Lean GPU Runtime Stacks**:
   - `:cuda` must use **host-based driver injection** (`libcuda.so.1`, `libnvidia-encode.so.1`, `libnvcuvid.so.1`) via NVIDIA Container Toolkit with zero in-container package bloat.
   - `:cuda13` must install **only** minimal video filter essentials (`cuda-nvrtc-13-4`, `cuda-cudart-13-4`, `libnpp-13-4`). Never install `libcublas`, `libcusolver`, `libcusparse`, `libcufft`, `libcurand`, or `cuda-compat`.
   - `:amd` must use **Mesa Gallium VA-API + Vulkan RADV** (`mesa-libgallium`, `mesa-vulkan-drivers`). Never install ROCm compute SDKs for video transcoding.
9. **NASA/JPL Power of 10 Compliance**:
   - All code, scripts, Dockerfiles, and test suites must adhere to the adapted [NASA/JPL Power of 10](docs/principles.md) rules.
   - Enforces bounded loops, short functions (<= 60 lines), checked return codes (`set -euo pipefail`), average assertion density >= 2.0 per test, and zero warnings across all linters.
10. **Dynamic Remediation & Upstream Decoupling**:
   - All vulnerability patches, assembly updates, and entrypoint neutralizations must be idempotent and conditional.
   - If upstream upgrades a dependency to meet or exceed the target safe version, or eliminates runtime `apt-get` calls, the build must preserve upstream's clean state without downgrades or failure.
   - Even if upstream fixes 100% of their base CVEs and runtime bugs, the pipeline must ship the optimized, slimmed, flavor-isolated image automatically with zero release breaks.

---

## 3. Image Flavor Matrix

| Flavor | Target Hardware | Content Size | Virtual Size | Included Acceleration Stack |
| :--- | :--- | :--- | :--- | :--- |
| **`:intel`** | Intel Core Gen 8–14+, Arc Alchemist, Battlemage, N-series | **514 MB** | **1.76 GB** | Intel Media Driver (`iHD` 26.1+), Level Zero (`libze`), oneVPL, OpenCL ICD |
| **`:amd`** | AMD Radeon RX 5000–8000 series, Ryzen 6000–9000 APUs | **473 MB** | **1.65 GB** | Mesa Gallium (`radeonsi`), RADV Vulkan, AMDGPU DRM |
| **`:cuda`** | NVIDIA Pascal through Ada Lovelace (Host-based CUDA) | **473 MB** | **1.65 GB** | Host-injected driver hooks (`libcuda`, NVENC, NVDEC) with zero package bloat |
| **`:cuda13`** | NVIDIA Ada Lovelace, Blackwell (RTX 50xx), Hopper (CUDA 13.4) | **720 MB** | **2.33 GB** | Minimal NVIDIA CUDA 13.4 runtime + NVRTC & NPP video filters |
| **`:latest`** / **`:all`** | Universal multi-vendor default | **574 MB** | **2.00 GB** | Full Intel Media Driver, Mesa Gallium VA-API, and NVIDIA host driver hooks |

---

## 4. Repository Layout

```text
.
├── .agents/
│   └── skills/                    # Modular AI agent skills (cross-agent standard)
│       ├── build-flavor/          # /build-flavor: build specific flavor with size checks
│       ├── test-image/            # /test-image: run full container assertion suite
│       ├── lint-all/              # /lint-all: run hadolint, yamllint, shellcheck, pre-commit
│       ├── sync-upstream/         # /sync-upstream: track revenz/fileflows:latest digest
│       ├── security-audit/        # /security-audit: zero-CVE and NuGet vulnerability audit
│       └── prep-release/          # /prep-release: changelog, size audit, tag preparation
├── .claude/
│   ├── agents/                    # Specialized review agents (container-reviewer, docs-reviewer)
│   ├── settings.json              # Tool permissions and command whitelists
│   └── skills -> ../.agents/skills # Symlinked agent skills
├── .cursor/
│   └── rules/fileflows.mdc        # Cursor editor semantic rules
├── .devcontainer/
│   └── devcontainer.json          # Containerized development workspace definition
├── .github/
│   ├── ISSUE_TEMPLATE/            # Bug report and feature request forms
│   ├── workflows/                 # Multi-arch CI, build-and-release, and docs pipelines
│   ├── CODEOWNERS                 # Repository code ownership
│   ├── copilot-instructions.md    # GitHub Copilot agent directives
│   ├── FUNDING.yml                # Sponsor configuration
│   └── PULL_REQUEST_TEMPLATE.md   # Pull request verification checklist
├── .vscode/
│   ├── extensions.json            # Curated zero-shareware extensions
│   ├── settings.json              # Schemas, indentation, linter configurations
│   └── tasks.json                 # Build, test, lint, and docs tasks
├── .zed/
│   ├── settings.json              # Zed editor configuration
│   └── tasks.json                 # Zed development tasks
├── docs/                          # Material MkDocs documentation source
│   ├── badges/                    # Dynamic Shields.io JSON endpoints
│   ├── architecture.md            # Multi-stage design & rootfs squashing
│   ├── hardware-acceleration.md   # GPU pass-through, drivers, and flavor matrix
│   ├── security-hardening.md      # Zero-CVE policy and capability dropping
│   └── ...
├── tests/
│   ├── test_docs_consistency.py   # Markdown links, heading anchors, compose sync
│   ├── test_image.py              # Invariant assertions, size gates, live HTTP smoke
│   ├── requirements-test.txt      # Test runner dependencies (pytest, pyyaml)
│   └── run_tests.sh               # CI test runner wrapper
├── .cursorrules                   # Root Cursor compatibility pointer
├── .windsurfrules                 # Windsurf IDE agent directives
├── CLAUDE.md                      # Claude Code instructions
├── Dockerfile                     # Canonical multi-stage OCI build definition
├── Dockerfile.optimized           # Mirror of Dockerfile (kept in 100% sync)
├── docker-compose.yml             # Drop-in production Compose deployment
├── Makefile                       # Developer tasks (build, test, lint, format)
├── mkdocs.yml                     # Documentation site navigation and theme
└── version.txt                    # Pinned upstream version tracking
```

---

## 5. Agent Skills & Slash Commands

This repository implements standardized skills under `.agents/skills/` (compatible with Antigravity, Claude Code, Cursor, OpenCode, and Codex):

| Command | Skill Directory | Description |
| :--- | :--- | :--- |
| **`/build-flavor`** | [.agents/skills/build-flavor](.agents/skills/build-flavor/SKILL.md) | Build specific flavor (`all`, `intel`, `amd`, `cuda`, `cuda13`) with size gates |
| **`/test-image`** | [.agents/skills/test-image](.agents/skills/test-image/SKILL.md) | Run Pytest container assertion suite and HTTP smoke tests |
| **`/lint-all`** | [.agents/skills/lint-all](.agents/skills/lint-all/SKILL.md) | Run Hadolint, Yamllint, ShellCheck, pre-commit, and doc consistency checks |
| **`/sync-upstream`** | [.agents/skills/sync-upstream](.agents/skills/sync-upstream/SKILL.md) | Compare against `revenz/fileflows:latest`, bump version, and test build |
| **`/security-audit`** | [.agents/skills/security-audit](.agents/skills/security-audit/SKILL.md) | Run Trivy scans, verify Pebble purge, and validate NuGet dependency versions |
| **`/prep-release`** | [.agents/skills/prep-release](.agents/skills/prep-release/SKILL.md) | Verify git status, update `CHANGELOG.md`, audit sizes, and validate tags |

---

## 6. Build & Test Commands

### Using Make
```bash
make help               # Display all available targets
make build              # Build universal default flavor (:latest / :all)
make build-all          # Build all 5 flavors locally
make build-intel        # Build Intel flavor (:intel)
make build-amd          # Build AMD flavor (:amd)
make build-cuda         # Build host-based CUDA flavor (:cuda)
make build-cuda13       # Build minimal CUDA 13.4 flavor (:cuda13)
make test               # Run Pytest suite against local image
make test-docs          # Run documentation & anchor consistency tests
make lint               # Run Hadolint, Yamllint, and ShellCheck
make format-check       # Verify YAML and Shell formatting
make docs-serve         # Launch local MkDocs live-reload server
```

### Direct CLI Commands
```bash
# Build universal image
docker build -t ghcr.io/lusoris/fileflows-real-image:latest --build-arg FLAVOR=all .

# Linting
hadolint --config .hadolint.yaml Dockerfile
yamllint -c .yamllint.yml .
shellcheck tests/run_tests.sh

# Pytest assertion suite
pytest tests/test_docs_consistency.py -v
TEST_IMAGE=ghcr.io/lusoris/fileflows-real-image:latest pytest tests/ -v
```

---

## 6. Prohibitions & Anti-Patterns

- **NEVER install `dotnet-sdk`** in the container image.
- **NEVER add `-dev` packages** to production stages.
- **NEVER use `read_only: true`** in Compose without testing upstream's `docker-entrypoint.sh` (upstream dynamically creates users and writes startup logs).
- **NEVER install heavy math/AI packages** (`libcublas`, `libcusolver`, `libcusparse`, `libcufft`, `ROCm`) into transcoding images.
- **NEVER let [Dockerfile](Dockerfile) and [Dockerfile.optimized](Dockerfile.optimized) drift** — they must remain identical.
- **NEVER break branch protection** on `main` — all CI quality gates must pass before merge.
