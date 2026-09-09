# Hardware Acceleration

FileFlows Real Image is engineered for seamless GPU transcoding out of the box. All essential driver stacks, runtimes, and libraries are pre-baked into the image at build time.

---

## Intel QuickSync Video (QSV & VA-API)

Supported architectures: Intel Core 6th Gen (Skylake) through 14th+ Gen, Intel Arc Alchemist/Battlemage dGPUs, and Intel N-series processors (N100/N200/N305).

### Modern Unified Driver Stack (Xe, Xe2, & Gen8+)
The image pre-bakes Intel's modern unified driver stack and purges obsolete legacy drivers (like `i965` for pre-2015 chips):
- `intel-media-va-driver-non-free`: The official Intel Media Driver (iHD, v26.1.2+). It natively supports both the classic `i915` kernel driver and the modern Linux `xe` kernel DRM driver (`xe.ko`). It fully accelerates modern **Xe2 (Battlemage BMG, Lunar Lake)**, **Xe (Arc Alchemist DG2, Arrow Lake, Meteor Lake, Raptor Lake, Alder Lake, Tiger Lake)**, as well as older Gen 8/9/11 hardware.
- `libze-intel-gpu1`: Intel oneAPI Level Zero GPU driver providing direct low-overhead hardware submission on modern Xe and Xe2 architectures.
- `intel-opencl-icd`: Intel Compute Runtime for OpenCL-based HDR tonemapping and color grading filters.
- `libvpl2` & `libmfx-gen1.2`: Intel oneVPL GPU runtime for direct QSV transcode pipelines.

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

## AMD Radeon & Ryzen APU (Mesa VA-API)

Supported architectures: AMD RDNA 2 (Radeon RX 6000), RDNA 3 / 3.5 (Radeon RX 7000, Ryzen 7000/8000/AI 300 APUs with dual AV1 encoders), and RDNA 4 (RX 8000+).

### Modern Driver Stack
- `mesa-va-drivers`: Official open-source Mesa Gallium driver (`radeonsi_drv_video.so`) providing hardware-accelerated H.264, HEVC, and AV1 encode/decode via VA-API.
- **Zero Legacy Baggage**: Deprecated APIs (VDPAU, UVD/VCE legacy wrappers) are completely omitted.

### Compose Configuration
AMD hardware exposes VA-API interfaces via `/dev/dri`:

```yaml
services:
  fileflows:
    image: ghcr.io/lusoris/fileflows-real-image:latest
    devices:
      - /dev/dri:/dev/dri
```

---

## NVIDIA GPU (NVENC & NVDEC)

Supported architectures: Turing (GTX 1660 / RTX 20xx), Ampere (RTX 30xx), Ada Lovelace (RTX 40xx with dual 8th-Gen NVENC AV1 engines), and Blackwell (RTX 50xx / B200 with 9th-Gen NVENC).

### Zero In-Image Driver Bloat
We intentionally do NOT install static `nvidia-driver-*` or bloated `cuda-toolkit` packages inside the image:
- The container sets `NVIDIA_DRIVER_CAPABILITIES=compute,video,utility` and `NVIDIA_VISIBLE_DEVICES=all`.
- At runtime, the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) dynamically mounts the host's active modern NVIDIA driver libraries (`libcuda.so`, `libnvcuvid.so`, `libnvidia-encode.so`) directly into the container.
- This prevents host-container driver version mismatches, eliminates hundreds of megabytes of CUDA SDK bloat, and guarantees compatibility with the latest NVIDIA drivers.

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
