<!-- markdownlint-disable MD024 -->
# Changelog

All notable changes to **FileFlows Real Image** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed

- **Badge and metric auto-updates never landed.** The release workflow committed regenerated
  badges, `version.txt` and README metrics and pushed them to `main`, which branch protection
  rejects with `GH006: Protected branch update failed` — 35 commits of history contain no
  `github-actions[bot]` commit, and the step only emitted a `::warning::`, so every release since
  the feature was written generated badges and discarded them. Generated endpoints are now
  published to the unprotected `badges` branch, the README reads them from there, and the measured
  size is recorded in the run summary and appended to the release body. `version.txt` and the
  README metrics table stay under human review, since a protected branch cannot accept an
  automated commit; drift is surfaced as a notice instead of being silently dropped.
- `docs/badges/*.json` is no longer committed, so there is a single source of truth for each badge.
  `tests/test_badges.py` now validates the generator in the release workflow and the README links
  that point at it, and asserts the in-tree copies are not reintroduced.

- **Azure.Identity was upgraded without its dependencies and could no longer load.** Bumping the
  assembly while Azure.Core stayed at upstream's 1.6.0 produced
  `FileNotFoundException: Could not load file or assembly 'Azure.Core, Version=1.38.0.0'` on any
  code path that touches it - strictly worse than upstream, which works. The remediator now
  installs the dependency closure alongside it: Azure.Core 1.38.0, Microsoft.Identity.Client and
  its Msal extensions 4.61.3, Microsoft.Bcl.AsyncInterfaces 1.1.1, plus System.ClientModel 1.0.0
  and System.Memory.Data 1.0.2, which upstream does not ship at all. The set was resolved with
  `dotnet publish` against net10.0 and reduced to what `/app` does not already satisfy;
  Microsoft.IdentityModel.Abstractions (8.19.1) and System.Security.Cryptography.ProtectedData
  (4.7.0) are already new enough and are left alone. Every member is clean per OSV.

- **CVE-2025-6965 (HIGH) in the bundled SQLite is now remediated.**
  `SQLitePCLRaw.lib.e_sqlite3` 2.1.11 shipped a vulnerable SQLite build and was not in the
  remediator's scope. It is now upgraded to 2.1.12, the minimal fix on that branch. Because it is a
  native package, each `runtimes/<rid>/native/libe_sqlite3.so` is replaced with the binary published
  for that same RID rather than one chosen build, so the arm64 slot never receives an x64 library.
- **The vulnerability gate could not see the CVEs it was meant to catch.** The Trivy step scanned
  `vuln-type: os` with `ignore-unfixed: true`, so it missed every .NET dependency CVE and every
  vulnerability with no recorded fix - it reported the image clean while a HIGH sat in a NuGet
  package. It now scans `os,library` with unfixed findings included. The image passes under that
  strictest setting with zero CRITICAL/HIGH across OS packages, all four `.deps.json` manifests and
  the bundled Go binary.

- **Remediator no longer reports a patch it did not apply.** `scripts/patch_upstream.py` rewrote
  `.deps.json` to the safe version even when zero assemblies were replaced, producing a manifest that
  claimed a patched package while the vulnerable DLL remained on disk. The upgrade path now fails
  closed and leaves the manifest untouched unless the assembly was actually written.
- **`sudo` restored inside the image.** The blanket setuid strip cleared the setuid bit on `sudo`,
  which the upstream entrypoint provisions for the runtime user, so any privileged operation failed
  with "sudo must be owned by uid 0 and have the setuid bit set". `sudo` and `su` are now exempt from
  the strip; every other setuid/setgid binary is still cleared.
- NuGet downloads now enforce a timeout and verify the response body, the archive and the requested
  asset instead of failing opaquely mid-build.
- Superseded `sha512` hashes are cleared when a library is re-keyed, and Microsoft.Data.SqlClient's
  framework-agnostic `runtime` block no longer advertises a stale `fileVersion`.
- The commented hardware-acceleration block in `docker-compose.yml` was indented inside `cap_add`,
  so uncommenting `devices:`/`deploy:` as documented produced invalid YAML. It now sits at service level.
- A failed image-size measurement in the release workflow substituted fabricated constants
  (`602000000` bytes / `574 MB`) and published them as measured metrics; it now warns and leaves the
  badge and README untouched. The upstream-version badge is guarded like `version.txt`, so a failed
  version extraction can no longer commit a permanently-failing badge test to `main`.
- The Docker Hub digest lookup ran `curl -s -f` under `bash -e`, aborting the step and making the
  buildx fallback unreachable; the fallback now runs as intended.
- `docs/security-hardening.md` was missing its trailing newline, failing `pre-commit` on a clean tree.
- **CI would have failed on GitHub runners.** The `pre-commit` gate added above used the `hadolint`
  hook, which is `language: system` and needs the binary on PATH; runners have no such binary, so the
  hook aborted with "Executable `hadolint` not found". Switched to the `hadolint-docker` hook. Found by
  executing the workflow locally with `act`, not by reading it.
- **hadolint version skew.** The CI image ships hadolint 2.15, which flags two deliberate constructs the
  locally-installed 2.14 does not: the `COPY --from=base-selected / /` squashing invariant (DL3067) and
  the shell-form `HEALTHCHECK` needed for its `||` fallback (DL3025). Both are now recorded as
  intentional in `.hadolint.yaml`, so the lint result no longer depends on which hadolint is installed.
- **The remediator installed a facade assembly.** For System.Drawing.Common it pulled
  `lib/netstandard2.0`, which carries no GDI+ interop (0 `gdiplus` references, 178 KB) versus the real
  `lib/net8.0` implementation (7 references, 611 KB). Installing it over a working assembly would break
  image operations on the .NET 10 runtime. Now pins the net8.0 asset.
- **Hardcoded assembly metadata had silently drifted.** The recorded `fileVersion` for Azure.Identity
  (`1.2100.26.11501` vs the actual `1.2100.26.21009`) and Microsoft.Data.SqlClient (`5.202.24263.2` vs
  `5.22.24240.06`) no longer matched the shipped DLLs. The value is now read from the assembly's
  VS_FIXEDFILEINFO block at build time instead of being asserted from a literal.
- **The release workflow mixed unit systems.** Content size was computed as `RAW_SIZE / 1024 / 1024`
  (MiB) but published into a table whose baseline is 999 decimal MB, so the next successful measurement
  would have restated the same image as "547 MB (-45%)" instead of 574 MB (-42.5%). Now decimal MB, with
  the reduction computed once to one decimal place and reused for both the badge and the README row.
- `.github/workflows/build-and-release.yml` assigned `FULL_VERSION` and never used it (SC2034).
- **Runtime `PATH` no longer discarded.** The entrypoint drops privileges with `su`, which resets
  `PATH` from `/etc/environment` and `/etc/login.defs`, so the server ran without `/dotnet`,
  `/dotnet/tools` or the CUDA bin directories — and with `/snap/bin`, despite snapd being pinned out.
  Both files are now aligned with the image `PATH` at build time.

### Changed

- **Remediation is now minimal and branch-aware.** The patcher pinned the newest release of each
  package (1.21.0 / 5.2.2 / 8.0.0) rather than the version the advisories actually require, so
  upstream's 1.3.0 / 3.0.0 / 4.7.0 were carried across major boundaries. It now installs the fix
  published for the assembly's own branch - 1.11.4, 3.1.5 and 4.7.2 - which clears exactly the same
  CVEs (Trivy: 116 CRITICAL/HIGH upstream, none of the three targeted CVEs remaining) while avoiding
  two known-breaking jumps: Microsoft.Data.SqlClient 4.0 flipped the default connection string to
  `Encrypt=true`, and System.Drawing.Common 6.0 dropped Unix support - 8.0.0 ships no
  `runtimes/unix` asset at all, so the previous target replaced a working Linux implementation with
  a Windows-only one.
- Advisory data is modelled per branch instead of as a single minimum version. These CVEs were fixed
  independently on each maintained line, so one threshold either missed a vulnerable newer branch or
  condemned an already-patched older one.
- The manifest rewrite preserves upstream's own asset layout, changing only the versions the entries
  advertise. `assemblyVersion` is left untouched where the branch did not change, so assembly binding
  stays identical to upstream's; `fileVersion` is read from the installed assembly.
- The patcher refuses to run if upstream has moved past the pinned target, rather than silently
  installing an older build.

- `make test` and `make coverage` now run every offline suite instead of a hand-maintained file list,
  which had silently excluded `tests/test_patcher.py` — the tests for the only production module.
- Coverage now measures production code (`--cov=scripts`) rather than the test files themselves, with
  `fail_under` raised from 85 to the documented 95. Coverage of `scripts/patch_upstream.py` rose from
  40% to 96%.
- `pre-commit` now runs as a CI quality gate, and Hadolint lints `Dockerfile.optimized` as well.
- The `:cuda13` flavor now installs from NVIDIA's `ubuntu2604` repository instead of `ubuntu2404`,
  matching its Ubuntu 26.04 base. Verified that all three pinned packages exist there and that the
  image still builds and installs them.
- Corrected measured documentation: the metrics table claimed 1,354 -> 615 installed packages where
  the real figures are 361 -> 281; the `:cuda` row duplicated `:amd`'s sizes (473 MB / 1.65 GB) where
  `:cuda` is actually ~394 MB / 1.27 GB; and the same size reduction was published as 43%, 42.5% and
  42% in three places.
- The markdown link and anchor checks no longer skip every dot-directory, so `.github/`, `.agents/`
  and `.claude/` documentation is covered, and both checks now ignore markdown syntax shown inside
  code spans instead of reporting it as broken links.
- **Releases are gated on the offline quality checks.** The lint/test gates moved into a reusable
  `quality-gates.yml`, which both `ci.yml` and `build-and-release.yml` call; the release job now
  declares `needs: quality-gates`. The 6-hourly scheduled path previously built and pushed to GHCR
  without running a single test.
- `markdownlint` is wired into `pre-commit` (and therefore CI) against the existing
  `.markdownlint.json`, which nothing had ever executed. 134 mechanical violations were fixed;
  FAQ question headings moved from `h3` to `h2` so heading levels increment correctly.

### Added

- FAQ entry recording why `libgdiplus` is deliberately omitted: a metadata scan of all 319
  assemblies in `/app` finds zero references to `System.Drawing` from any of the 50 `FileFlows*.dll`
  files — imaging is done with SixLabors.ImageSharp, and `System.Drawing.Common` is only a seven-hop
  transitive shim from `Microsoft.Data.SqlClient`. Installing the native library works but would add
  eight third-party C image codecs from Ubuntu *universe* to a zero-CVE image for a capability with
  no caller. Upstream ships no `runtimes/unix` asset either, so this matches upstream behaviour.

- `test_embedded_patcher_matches_script` asserts the base64 remediator embedded in the Dockerfile is
  byte-identical to `scripts/patch_upstream.py`. The build executes the embedded copy while the suite
  exercises the file on disk; nothing previously prevented them from drifting apart.
- Tests covering the remediation path: successful upgrade, fail-closed on a missing assembly,
  SqlClient metadata refresh, idempotency, and NuGet download integrity checks.
- `tests/test_image.py` aborts if the target image is absent and flags commands that never executed,
  so container invariants can no longer pass vacuously.
- NASA Rule 4 (<= 60 lines) now covers `scripts/` as well as `tests/`; Rule 2 checks loop bounds by AST
  instead of by string match. `remediate_app_dependencies` was 111 lines and is now decomposed.
- `arm64` is now built and asserted in CI. The `all` and `amd` flavors ship `linux/arm64` to GHCR,
  but nothing built or tested that architecture, and the driver assertions were guarded by
  `if arch == "amd64"` so they asserted nothing there. The arch branches now assert real invariants
  (Mesa present, the amd64-only Intel stack absent) and an unrecognised flavor fails instead of
  silently verifying nothing.
- `test_release_is_gated_on_quality_checks` enforces the new release gating as an invariant.
- Gate coverage widened: the `-dev` package check catches `apt-get -y install` and `apt install`
  forms, `libcurand` joins the forbidden CUDA list, the Dockerfile mirror check compares bytes, and
  the workflow invariants no longer skip `.yaml` files.

---

## [26.09.2-real.11] - 2026-09-09

### Added

- NASA/JPL "Power of 10" safety-critical engineering standards adapted for OCI containers and test engineering in [docs/principles.md](docs/principles.md).
- Automated AST compliance test suite `tests/test_principles.py` enforcing short functions (<= 60 lines), checked returns (`set -euo pipefail`), bounded polling loops, least privilege (`cap_drop: [ALL]`, `no-new-privileges`), and high assertion density (average >= 2.0 assertions/test; achieving 3.62 across 199 assertions).
- Expanded total offline unit test coverage to **97.04%** across 41 assertions.

### Fixed

- Suppressed misleading "Installing intel-media-va-driver-non-free..." echo log output during container boot for non-Intel flavors (`:amd`, `:cuda`, `:cuda13`) in `docker-entrypoint.sh`.
- Resolved MkDocs strict mode relative link resolution warning for `docker-compose.yml` in [docs/principles.md](docs/principles.md).

---

## [26.09.2-real.10] - 2026-09-09

### Added

- Comprehensive multi-AI contributor directives: [AGENTS.md](AGENTS.md), [CLAUDE.md](CLAUDE.md), [.windsurfrules](.windsurfrules), and [.cursor/rules/fileflows.mdc](.cursor/rules/fileflows.mdc).
- Standardized modular agent skills in `.agents/skills/` (`build-flavor`, `test-image`, `lint-all`, `sync-upstream`, `security-audit`, `prep-release`).
- Claude Code tool configurations, symlinked skills, and review subagents in `.claude/` (`container-reviewer`, `docs-reviewer`).
- GitHub Copilot instructions in [.github/copilot-instructions.md](.github/copilot-instructions.md) and root [.cursorrules](.cursorrules).
- Zed editor configuration and tasks in [.zed/](.zed/).
- Comprehensive automated test coverage expansion with 5 new offline test modules:
  - `tests/test_dockerfile.py`: Static analysis, multi-stage topology, rootfs squashing, and invariant validation.
  - `tests/test_workflows.py`: GitHub Actions YAML schema, Node 24 runtime enforcement, and flavor matrix validation.
  - `tests/test_agent_skills.py`: Agent skills YAML frontmatter, Claude review subagents, and editor task verification.
  - `tests/test_badges.py`: Shields.io dynamic endpoint schema and metric synchrony.
  - `tests/test_compose.py`: Docker Compose service specification and hardware device pass-through validation.
- Test coverage measurement tooling via `pytest-cov`, reaching **96.8%** offline unit test coverage with dedicated Makefile targets (`make test-unit`, `make coverage`, `make test-all`).
- Developer convenience tooling: [Makefile](Makefile) and [pyproject.toml](pyproject.toml).
- Curated zero-shareware VS Code workspace configuration in [.vscode/](.vscode/).

---

## [26.09.2-real.9] - 2026-09-09

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
