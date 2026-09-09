---
name: test-image
description: Run full Pytest container assertion suite and live runtime HTTP smoke test against a built FileFlows Real Image container.
---

# /test-image

Executes the automated verification suite against local container images to enforce all architectural invariants and runtime operational readiness.

## Invocation

```bash
/test-image [image_tag]
```

Default: `ghcr.io/lusoris/fileflows-real-image:latest`

## Test Coverage

1. **Base Hardening Invariants**:
   - OS is Ubuntu 26.04 Resolute (`/etc/os-release`).
   - Pebble binary and daemon directories (`/usr/bin/pebble`, `/var/lib/pebble`, `/etc/pebble`) completely purged.
   - Snap and snapd directories completely absent.
   - Zero `dotnet-sdk` packages installed; only `aspnetcore-runtime-10.0`.
   - Zero `-dev` header packages present in production stages.
   - Dead Windows and macOS runtime directories pruned from `/app`.
   - Utility binaries (`/usr/local/bin/docker`, `/usr/local/bin/dovi_tool`) present and executable.

2. **Hardware Acceleration Stack**:
   - Intel flavors: `intel-media-va-driver-non-free`, `intel-opencl-icd`, `libvpl2`, `libmfx-gen1.2`, `libze-intel-gpu1` present on `amd64`.
   - AMD flavor: `mesa-libgallium`, `mesa-vulkan-drivers`, `libdrm-amdgpu1` present.
   - CUDA host flavor: heavy math libraries (`cuda-libraries*`, `libcublas*`, `libcusolver*`) absent.
   - CUDA 13 flavor: minimal video filter packages (`cuda-nvrtc-13-4`, `cuda-cudart-13-4`, `libnpp-13-4`) present on `amd64`.
   - Legacy `i965-va-driver-shaders` purged across all flavors.

3. **Runtime Smoke & Web UI**:
   - Container boots in < 5 seconds.
   - No runtime `apt-get update` triggered in startup logs.
   - Web UI responds with HTTP 200 OK and serves `<title>FileFlows` on port 5000.

## Command

```bash
TEST_IMAGE=ghcr.io/lusoris/fileflows-real-image:latest pytest tests/test_image.py -v --tb=short
```
