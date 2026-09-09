# FileFlows Real Image

[![CI](https://github.com/lusoris/fileflows-real-image/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/lusoris/fileflows-real-image/actions/workflows/ci.yml)
[![Documentation](https://github.com/lusoris/fileflows-real-image/actions/workflows/docs.yml/badge.svg?branch=main)](https://lusoris.github.io/fileflows-real-image/)
[![Latest Release](https://img.shields.io/github/v/release/lusoris/fileflows-real-image?sort=semver)](https://github.com/lusoris/fileflows-real-image/releases/latest)
[![Ubuntu 26.04](https://img.shields.io/badge/Ubuntu-26.04%20Resolute-orange?logo=ubuntu)](https://ubuntu.com)
[![Base CVEs](https://img.shields.io/badge/Base%20CVEs-0%20(100%25%20Fixed)-brightgreen)](docs/security-hardening.md)
[![Image Size](https://img.shields.io/static/v1?label=Content%20Size&message=564%20MB%20(-43%25)&color=brightgreen)](docs/architecture.md)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20Project-F16061?logo=ko-fi&logoColor=white)](https://ko-fi.com/lusoris)
[![License: EUPL 1.2](https://img.shields.io/badge/License-EUPL%201.2-blue.svg)](LICENSE)

> A hardened, zero-CVE, production-ready multi-stage container for [FileFlows](https://fileflows.com) that slashes image size by 43%, eliminates base vulnerabilities, and boots in under 1 second.

Complete documentation is available at **[lusoris.github.io/fileflows-real-image](https://lusoris.github.io/fileflows-real-image/)**.

---

## Why FileFlows Real Image?

The upstream container (`revenz/fileflows:latest`, upstream version `26.09.2`) is distributed with full developer toolchains, unneeded service daemons, and missing drivers that slow down homelab and production deployments:

- **Full .NET 10 SDK Bloat (638 MB)**: Upstream installs `dotnet-sdk-10.0` instead of the lean `aspnetcore-runtime-10.0` (~96 MB).
- **15–20s Boot Delay**: Upstream triggers `apt-get update && apt-get install intel-media-va-driver-non-free` on **every container boot**. Real Image pre-bakes the driver stack for instant `< 1s` boot.
- **Go stdlib Base CVEs**: Upstream bundles Canonical's Rockcraft `pebble` service daemon, introducing 1 Critical (`CVE-2026-39821`) and 5 High CVEs. FileFlows never uses `pebble`.
- **140MB+ Dead Cross-Platform Runtimes**: Strips unused `win*` and `osx*` runtime folders that trigger false-positive Windows CVEs on Linux.
- **Rootfs Squashing**: Flattened via `FROM scratch COPY --from=base-builder / /` for 100% layer efficiency and zero retained deleted layer files.

---

## Metrics & Comparison

| Metric | Upstream (`revenz/fileflows:latest`) | Real Image (`ghcr.io/lusoris/fileflows-real-image:latest`) | Difference |
| :--- | :--- | :--- | :--- |
| **Content Size** | **999 MB** | **564 MB** | **-435 MB (-43.5%)** |
| **Virtual Disk Usage** | **3.57 GB** | **2.06 GB** | **-1.51 GB (-42.3%)** |
| **Installed Packages** | 1,354 packages | 615 packages | **-739 packages (-54.6%)** |
| **Base Image CVEs** | 1 Critical, 5 High, 2 Medium | **0 Critical, 0 High, 0 Medium** | **100% Resolved** |
| **Startup Delay** | 15–20s (`apt-get` on boot) | **< 1 second** (`already installed`) | **Instant Startup** |
| **Layer Efficiency** | ~75% (repeated layer writes) | **100% (Single squashed layer)** | **Maximum Density** |
| **.NET Runtime** | .NET 10.0.11 SDK (638 MB) | .NET 10.0.12 Runtime (~96 MB) | **Updated & Lean** |

---

## Quick Start

Run the container using [Docker Compose](docker-compose.yml):

```yaml
services:
  fileflows:
    image: ghcr.io/lusoris/fileflows-real-image:latest
    container_name: fileflows
    restart: unless-stopped
    init: true
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

```bash
docker compose up -d
```

Access the web interface at `http://localhost:19200`.

---

## Documentation

Detailed architectural and deployment guides are available in the [documentation suite](https://lusoris.github.io/fileflows-real-image/):

- **[Getting Started](docs/getting-started.md)**: Compose configuration, environment variables, healthchecks, and CLI deployment.
- **[Architecture & Build Pipeline](docs/architecture.md)**: Multi-stage build design, rootfs flattening, and .NET 10 runtime tuning.
- **[Hardware Acceleration](docs/hardware-acceleration.md)**: Setting up Intel QuickSync (VA-API/QSV), AMD Mesa VA-API, and NVIDIA Container Toolkit.
- **[Security Hardening](docs/security-hardening.md)**: Zero-CVE architecture, capability dropping (`cap_drop: [ALL]`), and zombie process reaping (`init: true`).
- **[CI/CD & Releases](docs/ci-cd-releases.md)**: Upstream-anchored versioning (`v<ver>-real.<rev>`), Dive efficiency gate, and 24h automated security rebuilds.
- **[Frequently Asked Questions](docs/faq.md)**: Why read-only rootfs fails, dynamic FFmpeg libraries, and custom flow scripts.

---

## Support & Sponsorship

If this project saves you disk space, network bandwidth, or boot time across your homelab or media server, support is available through [Ko-fi](https://ko-fi.com/lusoris).

[![Support on Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20Project-F16061?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/lusoris)

---

## License

This optimization recipe and Dockerfile are licensed under the [European Union Public Licence (EUPL-1.2)](LICENSE). FileFlows itself is subject to its original upstream licensing.
