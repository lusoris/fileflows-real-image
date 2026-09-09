# syntax=docker/dockerfile:1
ARG UPSTREAM_IMAGE=revenz/fileflows:latest

# ==============================================================================
# Stage 1: Pull upstream image and prune dead Windows/macOS runtimes from /app
# ==============================================================================
FROM ${UPSTREAM_IMAGE} AS upstream

# Prune unused Windows and macOS runtime libraries directly inside the container:
# - Saves ~140MB of disk footprint
# - Eliminates Windows-only CVE-2021-24112 (System.Drawing.Common) & CVE-2024-0056 (Microsoft.Data.SqlClient)
RUN find /app -type d -name "runtimes" -exec sh -c 'rm -rf "$1"/win* "$1"/osx*' _ {} \;

# ==============================================================================
# Stage 2: Upgraded, secure Ubuntu 26.04 base environment
# ==============================================================================
FROM ubuntu:26.04 AS base-builder

ARG DEBIAN_FRONTEND=noninteractive

# Update system packages, apply security upgrades, and install runtime dependencies
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        sudo tzdata wget ca-certificates curl tar xz-utils openssl locales \
        libfontconfig1 libfreetype6 pciutils vainfo \
        libssl3 libicu78 libavformat62 libavcodec62 libswscale9 \
        mesa-va-drivers \
        mkvtoolnix p7zip-full unrar \
        aspnetcore-runtime-10.0 && \
    if [ "$(dpkg --print-architecture)" = "amd64" ]; then \
        apt-get install -y --no-install-recommends \
            intel-media-va-driver-non-free i965-va-driver-shaders \
            libvpl2 libmfx-gen1.2 intel-opencl-icd; \
    fi && \
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
# Stage 3: Flatten rootfs to purge deleted layers (eliminates pebble from history)
# ==============================================================================
FROM scratch AS base-flat
COPY --from=base-builder / /

# ==============================================================================
# Stage 4: Final optimized FileFlows application image
# ==============================================================================
FROM base-flat

# Environment variables matching FileFlows configuration
ENV PATH=/dotnet:/dotnet/tools:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    DOTNET_ROOT=/dotnet \
    NVIDIA_DRIVER_CAPABILITIES=compute,video,utility \
    NVIDIA_VISIBLE_DEVICES=all \
    DOTNET_CLI_TELEMETRY_OPTOUT=true

# Copy custom binaries directly from upstream image
COPY --from=upstream /usr/local/bin/docker /usr/local/bin/docker
COPY --from=upstream /usr/local/bin/dovi_tool /usr/local/bin/dovi_tool

# Copy pruned application directory directly from upstream stage
COPY --from=upstream /app /app

# Ensure execution permissions on binaries and entrypoint
RUN chmod +x /usr/local/bin/docker /usr/local/bin/dovi_tool /app/docker-entrypoint.sh

# Expose web UI port
EXPOSE 5000/tcp

WORKDIR /app

ENTRYPOINT ["/app/docker-entrypoint.sh"]
