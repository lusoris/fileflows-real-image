# GitHub Copilot Instructions — FileFlows Real Image

You are an AI programming assistant working on **FileFlows Real Image** (`fileflows-real-image`), a hardened, multi-stage OCI container build system that repackages upstream `revenz/fileflows:latest` into lean, production-grade container images with pre-baked hardware acceleration stacks.

## Core Architectural Invariants

Whenever suggesting code, reviewing diffs, or editing configuration files, you must strictly preserve these invariants:

1. **Self-Contained Builds**:
   - Upstream assets are extracted exclusively using `COPY --from=upstream` or build stages in [Dockerfile](../Dockerfile).
   - Never rely on local extracted files (`app/`, `docker-bin/`) or host-side scripts.
2. **Zero Base CVEs & Rootfs Squashing**:
   - The Canonical Rockcraft `pebble` binary (`/usr/bin/pebble`) and directories (`/var/lib/pebble`, `/etc/pebble`) are purged.
   - The image layer history is flattened via `FROM scratch COPY --from=base-selected / /` to permanently erase vulnerable layer history.
3. **No .NET SDK Bloat**:
   - Never install `dotnet-sdk-*`. Always use `aspnetcore-runtime-10.0` (Ubuntu 26.04+). Dynamic Roslyn compilation in FileFlows executes in-memory on the runtime.
4. **No Dev Compilers**:
   - Never install `-dev` packages in production stages.
   - Use dynamic shared libraries (`libavcodec62`, `libavformat62`, `libswscale9`, `libicu78`, `libssl3`).
5. **Instant Startup**:
   - Pre-install vendor hardware drivers at build time so `docker-entrypoint.sh` never runs `apt-get update` on container start.
   - Neutralize runtime apt calls via `sed` in the build stage.
6. **Lean GPU Runtime Stacks**:
   - `:cuda` must use **host-based driver injection** (`libcuda.so.1`, `libnvidia-encode.so.1`, `libnvcuvid.so.1`) via NVIDIA Container Toolkit with zero in-container package bloat.
   - `:cuda13` must install **only** minimal video filter essentials (`cuda-nvrtc-13-4`, `cuda-cudart-13-4`, `libnpp-13-4`). Never install `libcublas`, `libcusolver`, `libcusparse`, `libcufft`, `libcurand`, or `cuda-compat`.
   - `:amd` must use **Mesa Gallium VA-API + Vulkan RADV** (`mesa-libgallium`, `mesa-vulkan-drivers`). Never install ROCm compute SDKs for video transcoding.
7. **Dockerfile Synchronization**:
   - [Dockerfile](../Dockerfile) and [Dockerfile.optimized](../Dockerfile.optimized) must remain 100% byte-identical.

## Flavor Matrix

| Flavor | Tag | Acceleration Stack | Content Size | Virtual Size |
| :--- | :--- | :--- | :--- | :--- |
| **Intel** | `:intel` | Intel Media Driver (`iHD` 26.1+), Level Zero (`libze`), oneVPL, OpenCL ICD | **514 MB** | **1.76 GB** |
| **AMD** | `:amd` | Mesa Gallium (`radeonsi` VA-API), RADV Vulkan, AMDGPU DRM | **473 MB** | **1.65 GB** |
| **NVIDIA (Host)** | `:cuda` | Host-injected driver hooks (`libcuda`, NVENC, NVDEC) with zero package bloat | **473 MB** | **1.65 GB** |
| **NVIDIA (CUDA 13.4)** | `:cuda13` | Minimal NVIDIA CUDA 13.4 runtime + NVRTC & NPP video filters | **720 MB** | **2.33 GB** |
| **Universal Default** | `:latest` / `:all` | Full Intel Media Driver, Mesa Gallium VA-API, and NVIDIA host driver hooks | **574 MB** | **2.00 GB** |

## Common Commands

```bash
make build              # Build universal default flavor (:latest / :all)
make build-intel        # Build Intel flavor (:intel)
make build-amd          # Build AMD flavor (:amd)
make build-cuda         # Build host-based CUDA flavor (:cuda)
make build-cuda13       # Build minimal CUDA 13.4 flavor (:cuda13)
make test-docs          # Run documentation consistency tests
make lint               # Run Hadolint, Yamllint, and ShellCheck
pre-commit run --all-files # Run all pre-commit hooks
```
