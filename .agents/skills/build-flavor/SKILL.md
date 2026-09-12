---
name: build-flavor
description: Build a specific FileFlows Real Image flavor (all, intel, amd, cuda, cuda13) or all flavors with multi-stage layer caching and size verification.
---

# /build-flavor

Builds hardened FileFlows container images locally with full architectural invariant checks.

## Invocation

```bash
/build-flavor [flavor] [--no-cache]
```

Flavors:

- `all` (default / `:latest`): Universal multi-vendor image (Intel QuickSync + AMD Mesa Gallium + NVIDIA host driver hooks)
- `intel` (`:intel`): Intel Core Gen 8–14+, Arc Alchemist/Battlemage (`intel-media-va-driver-non-free`, Level Zero, oneVPL)
- `amd` (`:amd`): AMD Radeon RX 5000–8000, Ryzen APUs (`mesa-libgallium` VA-API, RADV Vulkan)
- `cuda` (`:cuda`): NVIDIA Pascal through Ada Lovelace (host-injected `libcuda`, NVENC/NVDEC, zero container package bloat)
- `cuda13` (`:cuda13`): NVIDIA Ada Lovelace, Blackwell, Hopper (minimal CUDA 13.4 runtime + NVRTC & NPP video filters)

## Steps

1. Verify `Dockerfile` and `Dockerfile.optimized` are byte-identical:

   ```bash
   cmp -s Dockerfile Dockerfile.optimized || { echo "ERROR: Dockerfiles drifted!"; exit 1; }
   ```

2. Build target flavor:

   ```bash
   # Single flavor (e.g. intel)
   docker build -t ghcr.io/lusoris/fileflows-real-image:intel --build-arg FLAVOR=intel .

   # Or via make
   make build-intel
   ```

3. Inspect virtual size:

   ```bash
   docker image inspect ghcr.io/lusoris/fileflows-real-image:intel --format '{{.Size}}' | awk '{printf "Virtual Size: %.2f GB\n", $1/1073741824}'
   ```

4. Verify size gate:
   - Host-based flavors (`all`, `intel`, `amd`, `cuda`): <= 2.5 GB virtual size
   - Minimal CUDA 13 flavor (`cuda13`): <= 3.5 GB virtual size

## Invariant Guardrails

- Never extract files directly on the host; builds must remain fully self-contained.
- Never install `dotnet-sdk` or `-dev` packages in production stages.
- Flattened rootfs (`FROM scratch COPY --from=base-selected / /`) must be preserved to purge Rockcraft Pebble layer history.
