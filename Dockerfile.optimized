# syntax=docker/dockerfile:1
ARG UPSTREAM_IMAGE=revenz/fileflows:latest
ARG FLAVOR=all

# ==============================================================================
# Stage 1: Pull upstream image, prune Windows/macOS runtimes, and upgrade packages
# ==============================================================================
FROM ${UPSTREAM_IMAGE} AS upstream

# Prune unused Windows and macOS runtime libraries directly inside the container:
# - Saves ~140MB of disk footprint
# - Eliminates unused platform binaries
RUN find /app -type d -name "runtimes" -exec sh -c 'rm -rf "$1"/win* "$1"/osx*' _ {} \;

# Upgrade vulnerable and deprecated upstream NuGet assemblies across /app:
# - Azure.Identity: upgraded to latest modern release (1.21.0) with native net10.0 support
#   Resolves CVE-2023-36414, CVE-2024-29992, CVE-2024-35255
# - Microsoft.Data.SqlClient: upgraded to modern release (5.2.2)
#   Resolves CVE-2024-0056
# - System.Drawing.Common: upgraded to LTS release (8.0.0)
#   Resolves CVE-2021-24112
RUN echo "aW1wb3J0IHVybGxpYi5yZXF1ZXN0LCB6aXBmaWxlLCBpbywganNvbiwgb3MsIGdsb2IKCmRlZiBmZXRjaCh1cmwpOgogICAgcmVxID0gdXJsbGliLnJlcXVlc3QuUmVxdWVzdCh1cmwsIGhlYWRlcnM9eydVc2VyLUFnZW50JzogJ01vemlsbGEvNS4wJ30pCiAgICB3aXRoIHVybGxpYi5yZXF1ZXN0LnVybG9wZW4ocmVxKSBhcyByOgogICAgICAgIHJldHVybiB6aXBmaWxlLlppcEZpbGUoaW8uQnl0ZXNJTyhyLnJlYWQoKSkpCgojIDEuIEZldGNoIG1vZGVybiBOdUdldCBwYWNrYWdlcwp6X2F6dXJlID0gZmV0Y2goJ2h0dHBzOi8vYXBpLm51Z2V0Lm9yZy92My1mbGF0Y29udGFpbmVyL2F6dXJlLmlkZW50aXR5LzEuMjEuMC9henVyZS5pZGVudGl0eS4xLjIxLjAubnVwa2cnKQp6X3NxbCA9IGZldGNoKCdodHRwczovL2FwaS5udWdldC5vcmcvdjMtZmxhdGNvbnRhaW5lci9taWNyb3NvZnQuZGF0YS5zcWxjbGllbnQvNS4yLjIvbWljcm9zb2Z0LmRhdGEuc3FsY2xpZW50LjUuMi4yLm51cGtnJykKel9zZGMgPSBmZXRjaCgnaHR0cHM6Ly9hcGkubnVnZXQub3JnL3YzLWZsYXRjb250YWluZXIvc3lzdGVtLmRyYXdpbmcuY29tbW9uLzguMC4wL3N5c3RlbS5kcmF3aW5nLmNvbW1vbi44LjAuMC5udXBrZycpCgphenVyZV9kbGwgPSB6X2F6dXJlLnJlYWQoJ2xpYi9uZXQxMC4wL0F6dXJlLklkZW50aXR5LmRsbCcpCnNxbF9kbGwgPSB6X3NxbC5yZWFkKCdydW50aW1lcy91bml4L2xpYi9uZXQ4LjAvTWljcm9zb2Z0LkRhdGEuU3FsQ2xpZW50LmRsbCcpCnNkY19kbGwgPSB6X3NkYy5yZWFkKCdsaWIvbmV0c3RhbmRhcmQyLjAvU3lzdGVtLkRyYXdpbmcuQ29tbW9uLmRsbCcpCgojIDIuIFVwZGF0ZSBhc3NlbWJsaWVzIGFjcm9zcyAvYXBwCmZvciByb290LCBkaXJzLCBmaWxlcyBpbiBvcy53YWxrKCcvYXBwJyk6CiAgICBpZiAnQXp1cmUuSWRlbnRpdHkuZGxsJyBpbiBmaWxlczoKICAgICAgICB3aXRoIG9wZW4ob3MucGF0aC5qb2luKHJvb3QsICdBenVyZS5JZGVudGl0eS5kbGwnKSwgJ3diJykgYXMgZjoKICAgICAgICAgICAgZi53cml0ZShhenVyZV9kbGwpCiAgICBpZiAnTWljcm9zb2Z0LkRhdGEuU3FsQ2xpZW50LmRsbCcgaW4gZmlsZXM6CiAgICAgICAgd2l0aCBvcGVuKG9zLnBhdGguam9pbihyb290LCAnTWljcm9zb2Z0LkRhdGEuU3FsQ2xpZW50LmRsbCcpLCAnd2InKSBhcyBmOgogICAgICAgICAgICBmLndyaXRlKHNxbF9kbGwpCiAgICBpZiAnU3lzdGVtLkRyYXdpbmcuQ29tbW9uLmRsbCcgaW4gZmlsZXM6CiAgICAgICAgd2l0aCBvcGVuKG9zLnBhdGguam9pbihyb290LCAnU3lzdGVtLkRyYXdpbmcuQ29tbW9uLmRsbCcpLCAnd2InKSBhcyBmOgogICAgICAgICAgICBmLndyaXRlKHNkY19kbGwpCgojIDMuIFBhdGNoIGFsbCAuZGVwcy5qc29uIGZpbGVzCmZvciBwIGluIHNvcnRlZChnbG9iLmdsb2IoJy9hcHAvKiovKi5kZXBzLmpzb24nLCByZWN1cnNpdmU9VHJ1ZSkpOgogICAgd2l0aCBvcGVuKHAsICdyJywgZW5jb2Rpbmc9J3V0Zi04JykgYXMgZjoKICAgICAgICBkID0ganNvbi5sb2FkKGYpCgogICAgZm9yIHRhcmdldF9uYW1lLCB0YXJnZXQgaW4gZC5nZXQoJ3RhcmdldHMnLCB7fSkuaXRlbXMoKToKICAgICAgICBvbGRfYXogPSBbayBmb3IgayBpbiB0YXJnZXQgaWYgay5zdGFydHN3aXRoKCdBenVyZS5JZGVudGl0eS8nKV0KICAgICAgICBmb3IgayBpbiBvbGRfYXo6CiAgICAgICAgICAgIGVudHJ5ID0gdGFyZ2V0LnBvcChrKQogICAgICAgICAgICBlbnRyeVsncnVudGltZSddID0gewogICAgICAgICAgICAgICAgJ2xpYi9uZXQxMC4wL0F6dXJlLklkZW50aXR5LmRsbCc6IHsKICAgICAgICAgICAgICAgICAgICAnYXNzZW1ibHlWZXJzaW9uJzogJzEuMjEuMC4wJywKICAgICAgICAgICAgICAgICAgICAnZmlsZVZlcnNpb24nOiAnMS4yMTAwLjI2LjExNTAxJwogICAgICAgICAgICAgICAgfQogICAgICAgICAgICB9CiAgICAgICAgICAgIHRhcmdldFsnQXp1cmUuSWRlbnRpdHkvMS4yMS4wJ10gPSBlbnRyeQoKICAgICAgICBvbGRfc3FsID0gW2sgZm9yIGsgaW4gdGFyZ2V0IGlmIGsuc3RhcnRzd2l0aCgnTWljcm9zb2Z0LkRhdGEuU3FsQ2xpZW50LycpXQogICAgICAgIGZvciBrIGluIG9sZF9zcWw6CiAgICAgICAgICAgIGVudHJ5ID0gdGFyZ2V0LnBvcChrKQogICAgICAgICAgICBpZiAnZGVwZW5kZW5jaWVzJyBpbiBlbnRyeSBhbmQgJ0F6dXJlLklkZW50aXR5JyBpbiBlbnRyeVsnZGVwZW5kZW5jaWVzJ106CiAgICAgICAgICAgICAgICBlbnRyeVsnZGVwZW5kZW5jaWVzJ11bJ0F6dXJlLklkZW50aXR5J10gPSAnMS4yMS4wJwogICAgICAgICAgICBlbnRyeVsncnVudGltZVRhcmdldHMnXSA9IHsKICAgICAgICAgICAgICAgICdydW50aW1lcy91bml4L2xpYi9uZXQ4LjAvTWljcm9zb2Z0LkRhdGEuU3FsQ2xpZW50LmRsbCc6IHsKICAgICAgICAgICAgICAgICAgICAncmlkJzogJ3VuaXgnLAogICAgICAgICAgICAgICAgICAgICdhc3NldFR5cGUnOiAncnVudGltZScsCiAgICAgICAgICAgICAgICAgICAgJ2Fzc2VtYmx5VmVyc2lvbic6ICc1LjAuMC4wJywKICAgICAgICAgICAgICAgICAgICAnZmlsZVZlcnNpb24nOiAnNS4yMDIuMjQyNjMuMicKICAgICAgICAgICAgICAgIH0KICAgICAgICAgICAgfQogICAgICAgICAgICB0YXJnZXRbJ01pY3Jvc29mdC5EYXRhLlNxbENsaWVudC81LjIuMiddID0gZW50cnkKCiAgICAgICAgb2xkX3NkYyA9IFtrIGZvciBrIGluIHRhcmdldCBpZiBrLnN0YXJ0c3dpdGgoJ1N5c3RlbS5EcmF3aW5nLkNvbW1vbi8nKV0KICAgICAgICBmb3IgayBpbiBvbGRfc2RjOgogICAgICAgICAgICBlbnRyeSA9IHRhcmdldC5wb3AoaykKICAgICAgICAgICAgZW50cnlbJ3J1bnRpbWUnXSA9IHsKICAgICAgICAgICAgICAgICdsaWIvbmV0c3RhbmRhcmQyLjAvU3lzdGVtLkRyYXdpbmcuQ29tbW9uLmRsbCc6IHsKICAgICAgICAgICAgICAgICAgICAnYXNzZW1ibHlWZXJzaW9uJzogJzguMC4wLjAnLAogICAgICAgICAgICAgICAgICAgICdmaWxlVmVyc2lvbic6ICc4LjAuMjMuNTMxMDUnCiAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgIH0KICAgICAgICAgICAgZW50cnkucG9wKCdydW50aW1lVGFyZ2V0cycsIE5vbmUpCiAgICAgICAgICAgIHRhcmdldFsnU3lzdGVtLkRyYXdpbmcuQ29tbW9uLzguMC4wJ10gPSBlbnRyeQoKICAgICAgICBmb3IgcGtnX2VudHJ5IGluIHRhcmdldC52YWx1ZXMoKToKICAgICAgICAgICAgaWYgaXNpbnN0YW5jZShwa2dfZW50cnksIGRpY3QpIGFuZCAnZGVwZW5kZW5jaWVzJyBpbiBwa2dfZW50cnk6CiAgICAgICAgICAgICAgICBkZXBzID0gcGtnX2VudHJ5WydkZXBlbmRlbmNpZXMnXQogICAgICAgICAgICAgICAgaWYgJ0F6dXJlLklkZW50aXR5JyBpbiBkZXBzOiBkZXBzWydBenVyZS5JZGVudGl0eSddID0gJzEuMjEuMCcKICAgICAgICAgICAgICAgIGlmICdNaWNyb3NvZnQuRGF0YS5TcWxDbGllbnQnIGluIGRlcHM6IGRlcHNbJ01pY3Jvc29mdC5EYXRhLlNxbENsaWVudCddID0gJzUuMi4yJwogICAgICAgICAgICAgICAgaWYgJ1N5c3RlbS5EcmF3aW5nLkNvbW1vbicgaW4gZGVwczogZGVwc1snU3lzdGVtLkRyYXdpbmcuQ29tbW9uJ10gPSAnOC4wLjAnCgogICAgbGlicyA9IGQuZ2V0KCdsaWJyYXJpZXMnLCB7fSkKICAgIGZvciBvbGRfayBpbiBbayBmb3IgayBpbiBsaWJzIGlmIGsuc3RhcnRzd2l0aCgnQXp1cmUuSWRlbnRpdHkvJyldOgogICAgICAgIGxlID0gbGlicy5wb3Aob2xkX2spCiAgICAgICAgbGVbJ3BhdGgnXSA9ICdhenVyZS5pZGVudGl0eS8xLjIxLjAnCiAgICAgICAgbGVbJ2hhc2hQYXRoJ10gPSAnYXp1cmUuaWRlbnRpdHkuMS4yMS4wLm51cGtnLnNoYTUxMicKICAgICAgICBsaWJzWydBenVyZS5JZGVudGl0eS8xLjIxLjAnXSA9IGxlCgogICAgZm9yIG9sZF9rIGluIFtrIGZvciBrIGluIGxpYnMgaWYgay5zdGFydHN3aXRoKCdNaWNyb3NvZnQuRGF0YS5TcWxDbGllbnQvJyldOgogICAgICAgIGxlID0gbGlicy5wb3Aob2xkX2spCiAgICAgICAgbGVbJ3BhdGgnXSA9ICdtaWNyb3NvZnQuZGF0YS5zcWxjbGllbnQvNS4yLjInCiAgICAgICAgbGVbJ2hhc2hQYXRoJ10gPSAnbWljcm9zb2Z0LmRhdGEuc3FsY2xpZW50LjUuMi4yLm51cGtnLnNoYTUxMicKICAgICAgICBsaWJzWydNaWNyb3NvZnQuRGF0YS5TcWxDbGllbnQvNS4yLjInXSA9IGxlCgogICAgZm9yIG9sZF9rIGluIFtrIGZvciBrIGluIGxpYnMgaWYgay5zdGFydHN3aXRoKCdTeXN0ZW0uRHJhd2luZy5Db21tb24vJyldOgogICAgICAgIGxlID0gbGlicy5wb3Aob2xkX2spCiAgICAgICAgbGVbJ3BhdGgnXSA9ICdzeXN0ZW0uZHJhd2luZy5jb21tb24vOC4wLjAnCiAgICAgICAgbGVbJ2hhc2hQYXRoJ10gPSAnc3lzdGVtLmRyYXdpbmcuY29tbW9uLjguMC4wLm51cGtnLnNoYTUxMicKICAgICAgICBsaWJzWydTeXN0ZW0uRHJhd2luZy5Db21tb24vOC4wLjAnXSA9IGxlCgogICAgd2l0aCBvcGVuKHAsICd3JywgZW5jb2Rpbmc9J3V0Zi04JykgYXMgZjoKICAgICAgICBqc29uLmR1bXAoZCwgZiwgaW5kZW50PTIpCgpwcmludCgnU3RhZ2UgMTogU3VjY2Vzc2Z1bGx5IHVwZ3JhZGVkIEF6dXJlLklkZW50aXR5LCBNaWNyb3NvZnQuRGF0YS5TcWxDbGllbnQsIGFuZCBTeXN0ZW0uRHJhd2luZy5Db21tb24nKQo=" | base64 -d | python3


# ==============================================================================
# Stage 2: Common base environment (Ubuntu 26.04 + core libraries + .NET 10)
# ==============================================================================
FROM ubuntu:26.04 AS base-common

ARG DEBIAN_FRONTEND=noninteractive

# Update system packages, apply security upgrades, and install core runtime dependencies
RUN printf 'Package: snapd\nPin: release *\nPin-Priority: -10\n' > /etc/apt/preferences.d/nosnap.pref && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        sudo tzdata wget ca-certificates curl tar xz-utils openssl locales \
        libfontconfig1 libfreetype6 pciutils vainfo \
        libssl3 libicu78 libavformat62 libavcodec62 libswscale9 \
        mkvtoolnix p7zip-full unrar \
        aspnetcore-runtime-10.0 && \
    ln -s /usr/lib/dotnet /dotnet && \
    # Remove Canonical rockcraft pebble daemon and directories to eliminate Go stdlib CVEs
    rm -rf /usr/bin/pebble /var/lib/pebble /etc/pebble && \
    # Purge non-English locales (saves ~35MB)
    find /usr/share/locale -mindepth 1 -maxdepth 1 ! -name 'en*' -exec rm -rf {} + 2>/dev/null || true && \
    # Strip setuid/setgid bits across system binaries to prevent privilege escalation
    find /bin /sbin /usr/bin /usr/sbin -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true && \
    # Clean package caches, docs, manpages, and lintian
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/log/* \
           /usr/share/man /usr/share/doc /usr/share/info /usr/share/lintian /usr/share/bug

# ==============================================================================
# Stage 2a: Flavor Intel (Intel Arc, Xe, Lunar Lake, Battlemage, QuickSync QSV)
# ==============================================================================
FROM base-common AS base-intel

ARG DEBIAN_FRONTEND=noninteractive

RUN if [ "$(dpkg --print-architecture)" = "amd64" ]; then \
        apt-get update && \
        apt-get install -y --no-install-recommends \
            intel-media-va-driver-non-free \
            libvpl2 libmfx-gen1.2 intel-opencl-icd libze-intel-gpu1 && \
        apt-get clean && \
        rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/log/*; \
    fi

# ==============================================================================
# Stage 2b: Flavor AMD (AMD Radeon RX 5000/6000/7000/8000 series, APUs)
# ==============================================================================
FROM base-common AS base-amd

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        mesa-libgallium \
        mesa-vulkan-drivers \
        libdrm-amdgpu1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/log/*

# ==============================================================================
# Stage 2c: Flavor CUDA (Standard NVIDIA CUDA 12.x / NVENC / NVDEC)
# ==============================================================================
FROM base-common AS base-cuda

ARG DEBIAN_FRONTEND=noninteractive

RUN if [ "$(dpkg --print-architecture)" = "amd64" ]; then \
        curl -fsSL https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb -o /tmp/cuda-keyring.deb && \
        dpkg -i /tmp/cuda-keyring.deb && \
        rm -f /tmp/cuda-keyring.deb && \
        apt-get update && \
        apt-get install -y --no-install-recommends \
            cuda-libraries-12-8 \
            cuda-compat-12-8 && \
        apt-get clean && \
        rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/log/*; \
    fi

# ==============================================================================
# Stage 2d: Flavor CUDA 13 (Cutting-Edge NVIDIA CUDA 13.3+ Runtime & Libraries)
# ==============================================================================
FROM base-common AS base-cuda13

ARG DEBIAN_FRONTEND=noninteractive

RUN if [ "$(dpkg --print-architecture)" = "amd64" ]; then \
        curl -fsSL https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb -o /tmp/cuda-keyring.deb && \
        dpkg -i /tmp/cuda-keyring.deb && \
        rm -f /tmp/cuda-keyring.deb && \
        apt-get update && \
        apt-get install -y --no-install-recommends \
            cuda-libraries-13-3 \
            cuda-compat-13-3 && \
        apt-get clean && \
        rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/log/*; \
    fi

# ==============================================================================
# Stage 2e: Flavor All (Universal Multi-Vendor Default Image)
# ==============================================================================
FROM base-common AS base-all

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends mesa-libgallium && \
    if [ "$(dpkg --print-architecture)" = "amd64" ]; then \
        apt-get install -y --no-install-recommends \
            intel-media-va-driver-non-free \
            libvpl2 libmfx-gen1.2 intel-opencl-icd libze-intel-gpu1; \
    fi && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/log/*

# ==============================================================================
# Stage 3: Dynamic Flavor Selection
# ==============================================================================
ARG FLAVOR=all
FROM base-${FLAVOR} AS base-selected

# ==============================================================================
# Stage 4: Flatten rootfs to purge deleted layers (eliminates pebble from history)
# ==============================================================================
FROM scratch AS base-flat
COPY --from=base-selected / /

# ==============================================================================
# Stage 5: Final optimized FileFlows application image
# ==============================================================================
FROM base-flat

ARG FLAVOR=all

# OCI Standard Metadata Labels
LABEL org.opencontainers.image.title="FileFlows Real Image (${FLAVOR})" \
      org.opencontainers.image.description="Hardened, debloated, production-ready multi-stage image built from upstream revenz/fileflows" \
      org.opencontainers.image.url="https://github.com/lusoris/fileflows-real-image" \
      org.opencontainers.image.source="https://github.com/lusoris/fileflows-real-image" \
      org.opencontainers.image.licenses="EUPL-1.2" \
      org.opencontainers.image.flavor="${FLAVOR}" \
      org.opencontainers.image.vendor="lusoris"

# Environment variables matching FileFlows configuration & container performance optimizations
ENV PATH=/usr/local/cuda-13.3/bin:/usr/local/cuda-12.8/bin:/usr/local/cuda/bin:/dotnet:/dotnet/tools:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LD_LIBRARY_PATH=/usr/local/cuda-13.3/lib64:/usr/local/cuda-13.3/compat:/usr/local/cuda-12.8/lib64:/usr/local/cuda-12.8/compat:/usr/local/cuda/lib64 \
    DOTNET_ROOT=/dotnet \
    NVIDIA_DRIVER_CAPABILITIES=compute,video,utility \
    NVIDIA_VISIBLE_DEVICES=all \
    DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_NOLOGO=1 \
    DOTNET_EnableDiagnostics=0 \
    DOTNET_gcServer=1 \
    DOTNET_TieredPGO=1 \
    DOTNET_TC_QuickJitForLoops=1

# Copy custom binaries directly from upstream image
COPY --from=upstream /usr/local/bin/docker /usr/local/bin/docker
COPY --from=upstream /usr/local/bin/dovi_tool /usr/local/bin/dovi_tool

# Copy pruned application directory directly from upstream stage
COPY --from=upstream /app /app

# Ensure execution permissions on binaries and entrypoint, and neutralize runtime apt-get invocations
RUN chmod +x /usr/local/bin/docker /usr/local/bin/dovi_tool /app/docker-entrypoint.sh && \
    sed -i 's/apt-get update && apt-get install -y intel-media-va-driver-non-free/echo "Hardware acceleration pre-configured by FileFlows Real Image."/' /app/docker-entrypoint.sh

# Expose web UI port
EXPOSE 5000/tcp

# Healthcheck validating FileFlows web interface
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f -s http://127.0.0.1:5000/initial-config || curl -f -s http://127.0.0.1:5000/ || exit 1

WORKDIR /app

ENTRYPOINT ["/app/docker-entrypoint.sh"]
