# AGENTS.md — Agent & Contributor Directives

## Mission & Purpose
This repository provides a clean, hardened, production-ready multi-stage Dockerfile for FileFlows that builds directly from the bloated development image published upstream as `revenz/fileflows:latest`.

## Architectural Invariants
1. **Self-Contained Builds**:
   - The `Dockerfile` must NOT rely on local extracted files (`app/`, `docker-bin/`, etc.) or host-side scripts.
   - Any required assets from upstream must be pulled using `COPY --from=upstream` or multi-stage pipelines.
2. **Zero Base CVEs**:
   - The final image must maintain zero Critical/High base-image vulnerabilities.
   - The Canonical rockcraft `pebble` binary must remain stripped via rootfs flattening (`FROM scratch COPY --from=base-builder / /`).
3. **No .NET SDK Bloat**:
   - Never install `dotnet-sdk-*`. Always use `aspnetcore-runtime-*` (Ubuntu 26.04+).
4. **No Dev Compilers or Header Packages**:
   - Never install `-dev` packages in the production stage.
   - Use lean shared libraries (`libavcodec*`, `libavformat*`, `libswscale*`, `libicu*`, `libssl*`).
5. **Instant Startup**:
   - Pre-install `intel-media-va-driver-non-free` at build time so `docker-entrypoint.sh` never triggers `apt-get` on container start.
6. **Multi-Arch**:
   - Both `linux/amd64` and `linux/arm64` must build cleanly. Intel-specific packages must be conditionally scoped to amd64.
