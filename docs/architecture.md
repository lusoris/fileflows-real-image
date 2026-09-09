# Architecture & Build Pipeline

This document explains the technical architecture, optimization strategy, and engineering decisions behind the **FileFlows Real Image** build pipeline.

---

## The Upstream Image Problem

Upstream FileFlows (`revenz/fileflows:latest`) is distributed using a single-stage container build based on Ubuntu 26.04 Resolute that retains build tools, compilers, development packages, and extraneous platform runtimes.

An inspection of upstream reveals:

1. **Full .NET 10 SDK (638 MB)**: Upstream installs `dotnet-sdk-10.0`, which includes Roslyn compilers, MSBuild, project templates, and reference packs. At runtime, FileFlows only requires `aspnetcore-runtime-10.0` (~96 MB).
2. **Canonical Rockcraft `pebble` Daemon**: Upstream builds on a base image containing Canonical's `pebble` process supervisor compiled with an outdated Go standard library, introducing 1 Critical (`CVE-2026-39821`) and 5 High CVEs. FileFlows manages its own processes and never invokes `pebble`.
3. **C/C++ Header Packages (-dev packages)**: Unused header files (`libavcodec-dev`, `libssl-dev`, `libicu-dev`, `libc6-dev`, `linux-libc-dev`) consume over 120 MB of space.
4. **Dead Platform Runtimes**: The published `/app` folder includes runtimes for Windows (`win`, `win-x64`, `win-arm64`) and macOS (`osx`, `osx-x64`, `osx-arm64`), introducing known Windows CVEs (`CVE-2021-24112`, `CVE-2024-0056`) onto a Linux container.
5. **Startup Network Download**: Upstream's entrypoint script attempts `apt-get install intel-media-va-driver-non-free` on every boot, blocking startup by 15–20 seconds and downloading 30MB+ over the network.

---

## Multi-Stage Pipeline Design

The `Dockerfile` is completely self-contained. It pulls directly from upstream and transforms it across multiple stages without needing external files or host-side scripts.

```mermaid
flowchart TD
    Upstream[revenz/fileflows:latest] --> Stage1[Stage 1: app-source]
    Stage1 -->|Strip win* osx* runtimes| AppClean[/app cleaned]

    Ubuntu[Ubuntu 26.04 Resolute] --> Stage2[Stage 2: base-builder]
    AppClean --> Stage2

    subgraph BaseBuilder[base-builder execution]
        direction TB
        B1[nosnap.pref apt pinning]
        B2[apt install aspnetcore-runtime-10.0 + ffmpeg libs]
        B3[Pre-bake intel-media-va-driver-non-free]
        B4[Purge dev packages & build caches]
        B5[Purge non-English locales & docs]
        B6[Strip SUID/SGID bits]
        B7[rm -rf /usr/bin/pebble /var/lib/pebble]
    end

    Stage2 --> BaseBuilder
    BaseBuilder --> Stage3[Stage 3: production]
    Stage3 -->|FROM scratch COPY --from=base-builder / /| FinalImage[revenz/fileflows:optimized]
```

### Stage 1: `app-source`
- Sources `/app` and `/docker-bin` directly from upstream.
- Executes runtime pruning:
  ```bash
  find /app -type d -name "win*" -exec rm -rf {} +
  find /app -type d -name "osx*" -exec rm -rf {} +
  ```
- Strips Windows DLLs that trigger security scanner false positives.

### Stage 2: `base-builder`
- Builds a lean Ubuntu 26.04 foundation.
- Configures `/etc/apt/preferences.d/nosnap.pref` to prevent `snapd` installation.
- Installs `aspnetcore-runtime-10.0` instead of the SDK.
- Installs minimal runtime dynamic libraries (`libavcodec62`, `libavformat62`, `libswscale9`, `libvpl2`, `libicu78`, `libssl3`).
- Pre-installs `intel-media-va-driver-non-free`, `i965-va-driver-shaders`, and `mesa-va-drivers`.
- Purges `git`, `nano`, `gnupg`, non-English locales, man pages, and info directories.
- Strips SUID and SGID permissions (`chmod a-s`) across the entire root filesystem.
- Completely deletes any pebble traces: `/usr/bin/pebble`, `/var/lib/pebble`.

### Stage 3: `production` (Rootfs Flattening)
- Uses `FROM scratch` and copies the entire rootfs from `base-builder` (`COPY --from=base-builder / /`).
- This guarantees:
  - **Single Squashed Layer**: 100% layer efficiency score in `dive`.
  - **Zero Deleted Layer Retention**: Files removed in earlier build steps (like `pebble` or dev headers) are physically absent from all image layers, leaving zero residual vulnerabilities.

---

## .NET 10 Performance Optimization

The container configures runtime flags specifically optimized for high-throughput headless container workloads:

```dockerfile
ENV DOTNET_EnableDiagnostics=0 \
    DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=0 \
    DOTNET_GCCallbackRunning=0 \
    DOTNET_TieredPGO=1
```

- `DOTNET_EnableDiagnostics=0`: Disables tracing pipes and event listener overhead.
- `DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=0`: Retains ICU library support (`libicu78`) for correct multi-language media filename collation.
- `DOTNET_TieredPGO=1`: Activates Tiered Profile-Guided Optimization in the .NET 10 JIT compiler, accelerating CPU-bound pipeline loops.
