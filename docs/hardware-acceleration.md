# Hardware Acceleration & Image Flavors

FileFlows Real Image provides specialized, vendor-optimized container image flavors engineered for high-performance GPU transcoding. Each flavor pre-bakes the vendor-specific runtime and driver stack at build time, eliminating runtime package installations (`apt-get`) and stripping out unneeded driver bloat from competing vendors.

---

## Image Flavors Overview

| Flavor Tag | Target Hardware / Architecture | Content Size | Virtual Size | Driver Stack Included |
| :--- | :--- | :--- | :--- | :--- |
| **`:intel`** | Intel Core Gen 8–14+, Arc Alchemist, Battlemage, N-series | **514 MB** | **1.76 GB** | Intel Media Driver (iHD 26.1+), Level Zero (`libze`), oneVPL, OpenCL ICD |
| **`:amd`** | AMD Radeon RX 5000–8000 series, Ryzen 6000–9000 APUs | **473 MB** | **1.65 GB** | Mesa Gallium (`radeonsi`), RADV Vulkan, AMDGPU DRM |
| **`:cuda`** | NVIDIA Pascal through Ada Lovelace (Host-Based CUDA) | **473 MB** | **1.65 GB** | Host-injected driver hooks (`libcuda`, NVENC, NVDEC) with zero package bloat |
| **`:cuda13`** | NVIDIA Ada Lovelace, Blackwell (RTX 50xx), Hopper (CUDA 13.4) | **720 MB** | **2.33 GB** | Minimal NVIDIA CUDA 13.4 runtime + NVRTC & NPP video filters |
| **`:latest`** / **`:all`** | Universal multi-vendor default (Intel + AMD + NVIDIA runtimes) | **574 MB** | **2.00 GB** | Full Intel Media Driver, Mesa Gallium VA-API, and NVIDIA host driver hooks |

---

## 1. Intel QuickSync & Arc GPUs (`:intel`)

### Supported Hardware
- **Integrated Graphics**: Intel Core 8th Gen (Coffee Lake) through 14th Gen (Raptor Lake Refresh), Intel Core Ultra (Meteor Lake, Arrow Lake, Lunar Lake), and Intel N-series (N100, N200, N305).
- **Discrete GPUs**: Intel Arc Alchemist (A310, A380, A750, A770) and Intel Arc Battlemage (B570, B580).

### Pre-Baked Driver Stack
The `:intel` flavor is built specifically for Intel hardware with zero AMD or NVIDIA dependencies:
- **`intel-media-va-driver-non-free` (v26.1.2+)**: Intel Media Driver (iHD) with native dual support for both `i915` and modern Linux `xe` kernel DRM drivers (`xe.ko`). Accelerates AV1, HEVC 10-bit, and H.264 encode/decode.
- **`libze-intel-gpu1`**: Intel oneAPI Level Zero GPU driver for modern Xe and Xe2 architectures.
- **`intel-opencl-icd`**: Intel Compute Runtime for hardware-accelerated OpenCL HDR tone mapping (HDR10 to SDR) and color grading filters.
- **`libvpl2` & `libmfx-gen1.2`**: Intel oneVPL runtime for direct QSV transcode pipelines.
- **Zero Legacy Baggage**: Deprecated drivers (such as `i965` for pre-2015 CPUs) are purged.

### Compose Configuration (`:intel`)

```yaml
services:
  fileflows:
    image: ghcr.io/lusoris/fileflows-real-image:intel
    container_name: fileflows
    restart: unless-stopped
    devices:
      - /dev/dri:/dev/dri
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
```

---

## 2. AMD Radeon & Ryzen APUs (`:amd`)

### Supported Hardware
- **Radeon Discrete GPUs**: RDNA 1 (RX 5000), RDNA 2 (RX 6000), RDNA 3 / 3.5 (RX 7000), and RDNA 4 (RX 8000+).
- **Ryzen APUs**: Ryzen 4000/5000 (Vega), Ryzen 6000/7000/8000/AI 300 APUs with dual hardware AV1 engines.

### Pre-Baked Driver Stack
The `:amd` flavor slashes image content size down to **473 MB** (-53% vs upstream):
- **`mesa-libgallium`**: Official Mesa 26.0+ Gallium driver providing `/usr/lib/x86_64-linux-gnu/dri/radeonsi_drv_video.so` for hardware-accelerated VA-API H.264, HEVC, and AV1 encode/decode.
- **`mesa-vulkan-drivers` (RADV)**: High-performance AMD Vulkan driver for Vulkan-based video filters and compute.
- **`libdrm-amdgpu1`**: Direct AMDGPU kernel DRM interface.
- **Zero Intel/NVIDIA Bloat**: Omits all Intel Media Drivers and NVIDIA CUDA toolkits.

### Compose Configuration (`:amd`)

```yaml
services:
  fileflows:
    image: ghcr.io/lusoris/fileflows-real-image:amd
    container_name: fileflows
    restart: unless-stopped
    devices:
      - /dev/dri:/dev/dri
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
```

---

## 3. Host-Based NVIDIA CUDA (`:cuda`)

### Supported Hardware
- NVIDIA Pascal (GTX 10xx), Turing (GTX 1660, RTX 20xx), Ampere (RTX 30xx), and Ada Lovelace (RTX 40xx).

### Architecture & Driver Stack
The `:cuda` flavor delivers maximum efficiency by stripping out all in-container package bloat (such as unneeded cuBLAS and cuFFT AI libraries) and relying directly on host driver injection:
- Uses the official [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) to dynamically bind-mount `libcuda.so.1`, `libnvidia-encode.so.1` (NVENC), and `libnvcuvid.so.1` (NVDEC) at container startup.
- Configured with `NVIDIA_DRIVER_CAPABILITIES=compute,video,utility` and `NVIDIA_VISIBLE_DEVICES=all`.
- Drops image content size down to **473 MB** and virtual disk size to **1.65 GB** (slashing over 4.3 GB of wasted bloat).

### Compose Configuration (`:cuda`)

```yaml
services:
  fileflows:
    image: ghcr.io/lusoris/fileflows-real-image:cuda
    container_name: fileflows
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
```

---

## 4. Minimal Cutting-Edge NVIDIA CUDA 13.4 (`:cuda13`)

### Supported Hardware
- **Ada Lovelace** (RTX 4070, 4080, 4090 with dual 8th-Gen NVENC AV1 encoders).
- **Blackwell** (RTX 5070, 5080, 5090, B100, B200 with 9th-Gen NVENC).
- **Hopper** (H100, H200) and Ampere (RTX 30xx).

### Why CUDA 13.4 Minimal?
CUDA 13.4 introduces optimized compute kernels and modern hardware acceleration pipelines tailored for next-generation architectures like Blackwell (RTX 50xx). The `:cuda13` image is engineered strictly with the video transcode runtime essentials:
- **`cuda-nvrtc-13-4`**: NVIDIA Runtime Compilation library required for dynamic FFmpeg CUDA filter compilation (`scale_cuda`, `yadif_cuda`, `overlay_cuda`, etc.).
- **`cuda-cudart-13-4`**: Core CUDA 13.4 runtime API library.
- **`libnpp-13-4`**: NVIDIA Performance Primitives for NPP-based video filtering and color processing (`scale_npp`).
- **Zero AI Math Bloat**: Excludes `libcublas` (-850 MB), `libcusolver` (-390 MB), `libcusparse` (-380 MB), `libcufft` (-273 MB), and `cuda-compat` (-200 MB), slashing over 2.7 GB of unneeded libraries while retaining 100% video transcoding filter support.

### Compose Configuration (`:cuda13`)

```yaml
services:
  fileflows:
    image: ghcr.io/lusoris/fileflows-real-image:cuda13
    container_name: fileflows
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
```

---

## 5. Universal Default Image (`:latest`)

If you operate a mixed cluster with both Intel and AMD nodes, or prefer a single image that adapts to whatever GPU is available, use `ghcr.io/lusoris/fileflows-real-image:latest`. It pre-bakes the full Intel QuickSync stack, Mesa Gallium VA-API for AMD, and environment hooks for NVIDIA Container Toolkit, all within a compact 574 MB content footprint.

---

## Verification & Diagnostics

### VA-API (Intel / AMD)
Verify that your GPU encoder is accessible inside the container by running `vainfo`:

```bash
docker exec -it fileflows vainfo
```

Sample output confirming AV1, HEVC, and H.264 hardware encoding:
```text
VAProfileH264Main    : VAEntrypointEncSlice
VAProfileHEVCMain    : VAEntrypointEncSlice
VAProfileAV1Profile0 : VAEntrypointEncSlice
```

### NVIDIA (NVENC / NVDEC)
Verify that your NVIDIA GPU is recognized by running `nvidia-smi`:

```bash
docker exec -it fileflows nvidia-smi
```

### Troubleshooting `/dev/dri/renderD128` Permissions
If FileFlows cannot access the GPU device:
1. Verify device permissions on the host:
   ```bash
   ls -la /dev/dri
   ```
2. Identify the host group ID for `render` (typically `107` or `993` on Ubuntu/Debian).
3. If necessary, add the host group ID via `group_add` in `docker-compose.yml`:
   ```yaml
   services:
     fileflows:
       group_add:
         - "993"
   ```
