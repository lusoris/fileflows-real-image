# Hardware Acceleration

FileFlows Real Image is engineered for seamless GPU transcoding out of the box. All essential driver stacks, runtimes, and libraries are pre-baked into the image at build time.

---

## Intel QuickSync Video (QSV & VA-API)

Supported architectures: Intel Core 6th Gen (Skylake) through 14th+ Gen, Intel Arc Alchemist/Battlemage dGPUs, and Intel N-series processors (N100/N200/N305).

### Pre-Installed Driver Stack
- `intel-media-va-driver-non-free`: Modern Intel iHD driver (Gen9+ hardware).
- `i965-va-driver-shaders`: Legacy Intel i965 driver for older CPUs.
- `intel-opencl-icd`: OpenCL compute runtime for HDR tonemapping filters.
- `libvpl2` & `libmfx-gen1.2`: Intel oneVPL and Media SDK runtimes for direct QSV pipelines.

### Compose Configuration
Pass the Direct Rendering Infrastructure device `/dev/dri` to the container:

```yaml
services:
  fileflows:
    image: ghcr.io/lusoris/fileflows-real-image:latest
    devices:
      - /dev/dri:/dev/dri
    environment:
      - PUID=1000
      - PGID=1000
```

### Host Permissions
Ensure the user running the container belongs to the `video` and `render` groups on the host:

```bash
sudo usermod -aG video,render $USER
```

---

## AMD Radeon & APU (Mesa VA-API)

Supported architectures: AMD Ryzen APUs (Vega, RDNA2, RDNA3) and Radeon dedicated GPUs (RX 400 through RX 7000+ series).

### Pre-Installed Driver Stack
- `mesa-va-drivers`: Official open-source Mesa Gallium driver providing hardware-accelerated H.264, HEVC, and AV1 encode/decode via VA-API.

### Compose Configuration
AMD hardware also exposes VA-API interfaces via `/dev/dri`:

```yaml
services:
  fileflows:
    image: ghcr.io/lusoris/fileflows-real-image:latest
    devices:
      - /dev/dri:/dev/dri
```

---

## NVIDIA GPU (NVENC & NVDEC)

Supported architectures: Pascal (GTX 10xx), Turing (GTX 16xx / RTX 20xx), Ampere (RTX 30xx), Ada Lovelace (RTX 40xx), and Blackwell.

### Prerequisites
1. Host NVIDIA display drivers must be installed.
2. The [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) must be installed and configured on the host.

### Compose Configuration
Configure the GPU reservation block:

```yaml
services:
  fileflows:
    image: ghcr.io/lusoris/fileflows-real-image:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

Or when running via Docker CLI:

```bash
docker run --gpus all ... ghcr.io/lusoris/fileflows-real-image:latest
```

---

## Verification & Diagnostics

To confirm your GPU is recognized inside the container:

### Intel / AMD VA-API Verification
Run `vainfo` inside the running container:

```bash
docker exec -it fileflows vainfo
```

You should see an output listing supported entrypoints, such as:
```text
VAProfileH264Main : VAEntrypointEncSlice
VAProfileHEVCMain : VAEntrypointEncSlice
VAProfileAV1Profile0 : VAEntrypointEncSlice
```

### NVIDIA Verification
Run `nvidia-smi` inside the running container:

```bash
docker exec -it fileflows nvidia-smi
```

### Troubleshooting Permission Denied on `/dev/dri/renderD128`
If FileFlows fails to initialize the hardware encoder:
1. Check device permissions on the host:
   ```bash
   ls -la /dev/dri
   ```
2. Note the GID of the `render` group (commonly `107` or `993` on Ubuntu/Debian).
3. If necessary, pass the group ID via `group_add` in `docker-compose.yml`:
   ```yaml
   services:
     fileflows:
       group_add:
         - "993" # Host render group ID
   ```
