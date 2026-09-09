# Getting Started

This guide explains how to deploy and configure the **FileFlows Real Image** container on Linux, Windows (WSL2), or macOS using Docker Compose or the standard Docker CLI.

---

## Deployment with Docker Compose (Recommended)

Docker Compose provides declarative configuration and ensures clean volume and permission mapping.

### 1. Download Compose Configuration

Save the following `docker-compose.yml` to your desired directory:

```yaml
services:
  fileflows:
    # Image Flavors:
    #   ghcr.io/lusoris/fileflows-real-image:latest  - Universal default (Intel + AMD + NVIDIA runtimes)
    #   ghcr.io/lusoris/fileflows-real-image:intel   - Intel QuickSync & Arc optimized (514MB)
    #   ghcr.io/lusoris/fileflows-real-image:amd     - AMD Radeon & Ryzen APU optimized (473MB)
    #   ghcr.io/lusoris/fileflows-real-image:cuda    - Host-based NVIDIA acceleration for NVENC/NVDEC (470MB)
    #   ghcr.io/lusoris/fileflows-real-image:cuda13  - Minimal NVIDIA CUDA 13.4 runtime with video filters (720MB)
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
      # Bind mounts for your media libraries:
      # - /srv/media/movies:/media/movies
      # - /srv/media/tv:/media/tv
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
      # devices:
      #   - /dev/dri:/dev/dri

volumes:
  fileflows-data:
  fileflows-temp:
  fileflows-logs:
  fileflows-common:
```

### 2. Configure Environment Variables

Create a `.env` file alongside `docker-compose.yml`:

```env
PORT=19200
TZ=Europe/Berlin
PUID=1000
PGID=1000
```

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `19200` | Host port mapped to container HTTP Web UI (internal port 5000). |
| `TZ` | `UTC` | Timezone string (e.g. `America/New_York`, `UTC`). |
| `PUID` | `1000` | User ID under which FileFlows executes processing and creates files. |
| `PGID` | `1000` | Group ID for file permission consistency with host media storage. |

### 3. Launch the Container

```bash
docker compose up -d
```

Check the startup logs:

```bash
docker compose logs -f fileflows
```

Because hardware drivers and runtimes are pre-baked at image build time across all flavors (`intel`, `amd`, `cuda`, `cuda13`, `latest`), container startup takes less than **1 second** and never triggers `apt-get` on boot. For GPU pass-through configurations, consult the **[Hardware Acceleration Guide](hardware-acceleration.md)**.

---

## Deployment with Docker CLI

If you prefer deploying via `docker run`:

```bash
docker run -d \
  --name fileflows \
  --restart unless-stopped \
  --init \
  --security-opt no-new-privileges:true \
  --cap-drop ALL \
  --cap-add CHOWN \
  --cap-add SETUID \
  --cap-add SETGID \
  --cap-add DAC_OVERRIDE \
  -p 19200:5000 \
  -e TZ=UTC \
  -e PUID=1000 \
  -e PGID=1000 \
  -v fileflows-data:/app/Data \
  -v fileflows-temp:/temp \
  -v fileflows-logs:/app/Logs \
  -v fileflows-common:/common \
  -v /path/to/media:/media \
  ghcr.io/lusoris/fileflows-real-image:latest
```

---

## Healthcheck & Monitoring

The container includes a native Docker `HEALTHCHECK` defined directly in the image:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/api/status || exit 1
```

You can inspect the health status at any time:

```bash
docker inspect --format='{{json .State.Health}}' fileflows | jq
```

When monitored via tools like Portainer, Dockge, or Docker CLI, the container status will report `(healthy)`.

---

## Accessing the Web Interface

Once running, navigate to:

```text
http://<server-ip>:19200
```

Follow the on-screen setup wizard to configure your FileFlows libraries, processing nodes, and transcoding flows.
