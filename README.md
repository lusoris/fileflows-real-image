# FileFlows Real Image

> A multi-stage, hardened Dockerfile that transforms the fat development container published as `revenz/fileflows:latest` into a clean, production-ready image.

[![Ubuntu 26.04](https://img.shields.io/badge/Ubuntu-26.04%20Resolute-orange?logo=ubuntu)](https://ubuntu.com)
[![Docker](https://img.shields.io/badge/Docker-Multi--Stage-blue?logo=docker)](https://docs.docker.com/build/building/multi-stage/)
[![CI Quality Gates](https://github.com/lusoris/fileflows-real-image/actions/workflows/ci.yml/badge.svg)](https://github.com/lusoris/fileflows-real-image/actions/workflows/ci.yml)
[![CI Build & Release](https://github.com/lusoris/fileflows-real-image/actions/workflows/build-and-release.yml/badge.svg)](https://github.com/lusoris/fileflows-real-image/actions/workflows/build-and-release.yml)
[![License: EUPL 1.2](https://img.shields.io/badge/License-EUPL%201.2-blue.svg)](https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12)
[![Base CVEs](https://img.shields.io/badge/Base%20CVEs-0%20(100%25%20Fixed)-brightgreen)](#metrics--comparison)
[![Image Size](https://img.shields.io/static/v1?label=Content%20Size&message=564%20MB%20(-43%25)&color=brightgreen)](#metrics--comparison)

---

## The Problem with Upstream `revenz/fileflows:latest`

The official `revenz/fileflows:latest` image is distributed with full development toolchains and unnecessary build artifacts:

1. **Full .NET 10 SDK (638MB on disk)**: Upstream installs `dotnet-sdk-10.0` (compilers, templates, and targeting packs) for an application that only needs the lightweight runtime (`aspnetcore-runtime-10.0`).
2. **C/C++ Development Toolchain (-dev packages)**: Upstream installs `-dev` header packages (`libssl-dev`, `libicu-dev`, `libavformat-dev`, `libavcodec-dev`, `libswscale-dev`, `libmfx-dev`, `libvpl-dev`, `libc6-dev`, `linux-libc-dev`, and `manpages-dev`).
3. **15–20s Container Boot Delay**: The upstream entrypoint script checks for `intel-media-va-driver-non-free`. Because upstream omitted it from their build, **every single container boot** triggers `apt-get update && apt-get install -y intel-media-va-driver-non-free`, delaying startup by 15–20 seconds and downloading 30MB+ over the network.
4. **Go `stdlib 1.26.5` Base Image CVEs**: Upstream's base includes Canonical's Rockcraft `pebble` service daemon, introducing 1 Critical (`CVE-2026-39821`) and 5 High CVEs (`CVE-2026-56862`, `CVE-2026-56859`, `CVE-2026-56853`, `CVE-2026-46600`, `CVE-2026-33818`). FileFlows never uses `pebble`.
5. **140MB+ Dead Windows & macOS Runtimes**: Cross-platform publish outputs include `win`, `win-x64`, `win-arm64`, `osx`, `osx-x64`, and `osx-arm64` directories in `/app/*/runtimes`. In addition to bloat, the Windows DLLs trigger Critical `CVE-2021-24112` (`System.Drawing.Common 4.7.0`) and High `CVE-2024-0056` (`Microsoft.Data.SqlClient 3.0.0`).

---

## What This Project Does

This repository provides a self-contained, multi-stage `Dockerfile` that builds directly from the upstream image (`revenz/fileflows:latest`) without requiring local files or folders:

- **100% Zero Base CVEs**: Drops the unused `pebble` binary via rootfs squashing (`FROM scratch COPY --from=...`), clearing all 8 Go base CVEs.
- **ASP.NET Core Runtime (10.0.12)**: Replaces the full 638MB SDK with the lean runtime (~96MB), saving over 500MB while preserving in-memory Roslyn scripting and execution.
- **Production Shared Libraries**: Replaces all `-dev` packages with lean production shared libraries (`libavcodec62`, `libavformat62`, `libswscale9`, `libvpl2`, `libmfx-gen1.2`, `libicu78`, `libssl3`).
- **Instant Boot**: Pre-bakes `intel-media-va-driver-non-free` at build time so the container boots in `< 1s` without running `apt-get` on startup.
- **Pruned Dead Runtimes**: Strips all `win*` and `osx*` runtime folders from `/app` directly during build.
- **Hardware Acceleration Intact**: Full support for Intel QuickSync (VA-API/QSV via `intel-media-va-driver-non-free`, `i965-va-driver-shaders`, `libvpl2`, `libmfx-gen1.2`, `intel-opencl-icd`), AMD/Intel Mesa VA-API (`mesa-va-drivers`), and NVIDIA GPUs.

---

## Metrics & Comparison

| Metric | Upstream (`revenz/fileflows:latest`) | Real Image (`revenz/fileflows:optimized`) | Difference |
| :--- | :--- | :--- | :--- |
| **Content Size** | **999 MB** | **564 MB** | **-435 MB (-43.5%)** |
| **Virtual Disk Usage** | **3.57 GB** | **2.06 GB** | **-1.51 GB (-42.3%)** |
| **Installed Packages** | 1,354 packages | 615 packages | **-739 packages (-54.6%)** |
| **Base Image CVEs** | 1 Critical, 5 High, 2 Medium | **0 Critical, 0 High, 0 Medium, 0 Low** | **100% Resolved** |
| **Startup Delay** | 15–20s (`apt-get` on boot) | **< 1 second** (`already installed`) | **Instant Startup** |
| **.NET Runtime** | .NET 10.0.11 SDK (638 MB) | .NET 10.0.12 Runtime (~96 MB) | **Updated & Lean** |

---

## Quick Start (Pre-built Image)

Pull the pre-built image directly from GitHub Container Registry (GHCR):

```bash
docker pull ghcr.io/lusoris/fileflows-real-image:latest
```

---

## How to Build Locally

```bash
docker build -t revenz/fileflows:optimized .
```

To build from a specific upstream version tag instead of `latest`:

```bash
docker build --build-arg UPSTREAM_IMAGE=revenz/fileflows:26.09.2 -t revenz/fileflows:optimized .
```

---

## How to Run

### Using Docker Compose (Recommended)

A ready-to-use [`docker-compose.yml`](docker-compose.yml) structured according to the official [FileFlows Docker Generator](https://fileflows.com/docs/installation/docker) is included in the repository. Simply run:

```bash
docker compose up -d
```

To configure custom ports (default `19200`), timezone, or UID/GID, copy `.env.example` to `.env`:

```bash
cp .env.example .env
docker compose up -d
```

The standard `docker-compose.yml` uses the optimized image directly:

```yaml
services:
  fileflows:
    image: revenz/fileflows:optimized # or ghcr.io/lusoris/fileflows-real-image:latest
    container_name: fileflows
    restart: unless-stopped
    ports:
      - "${PORT:-19200}:5000"
    environment:
      - TZ=${TZ:-UTC}
      - PUID=${PUID:-1000}
      - PGID=${PGID:-1000}
    volumes:
      - fileflows-data:/app/Data
      - fileflows-temp:/temp
      - fileflows-logs:/app/Logs
      - fileflows-common:/common
      # Uncomment and adjust to map your media library:
      # - /path/to/media:/media
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETUID
      - SETGID
      - DAC_OVERRIDE
    # Optional Hardware Acceleration:
    # Intel / AMD VA-API / QSV:
    # devices:
    #   - /dev/dri:/dev/dri
    # NVIDIA GPU:
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: all
    #           capabilities: [gpu]

volumes:
  fileflows-data:
  fileflows-temp:
  fileflows-logs:
  fileflows-common:
```

Or run via Docker CLI:

```bash
docker run -d \
  --name fileflows \
  --restart unless-stopped \
  -p 19200:5000 \
  -e TZ=UTC \
  -e PUID=1000 \
  -e PGID=1000 \
  -v fileflows-data:/app/Data \
  -v fileflows-temp:/temp \
  -v fileflows-logs:/app/Logs \
  -v fileflows-common:/common \
  -v /path/to/media:/media \
  --device /dev/dri:/dev/dri \
  revenz/fileflows:optimized
```

---

## Testing & Quality Gates

This repository includes a pytest assertion suite ([tests/test_image.py](tests/test_image.py)) that rigorously verifies:
- **Base OS Hardening**: Confirms Ubuntu 26.04 Resolute base.
- **CVE Fixes**: Asserts `/usr/bin/pebble` and its state directories are completely purged.
- **Debloat & Cleanliness**: Asserts zero `dotnet-sdk` packages and zero `-dev` header packages are present.
- **Driver Pre-baking**: Asserts `intel-media-va-driver-non-free`, `i965-va-driver-shaders`, `libvpl2`, `libmfx-gen1.2`, and `intel-opencl-icd` are present.
- **Dead Runtimes**: Asserts all `win*` and `osx*` runtime directories are purged from `/app`.
- **Image Metrics**: Enforces size constraints (<= 650 MB content size, <= 2.5 GB virtual disk).
- **Runtime Web UI**: Boots the container and asserts `<title>FileFlows - Initial Configuration</title>` responds with HTTP 200 on port 19200 within 5 seconds.

### Run Tests Locally

```bash
# Install dependencies
pip install -r tests/requirements-test.txt

# Run assertion suite
pytest tests/test_image.py -v --tb=short
```

Or execute the test runner script:

```bash
bash tests/run_tests.sh
```

---

## License

This Dockerfile and optimization recipe is licensed under the [European Union Public Licence (EUPL-1.2)](LICENSE). FileFlows itself is subject to its original upstream licensing.
