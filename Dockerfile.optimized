# syntax=docker/dockerfile:1
ARG UPSTREAM_IMAGE=revenz/fileflows:latest

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
RUN python3 << 'EOF'
import urllib.request, zipfile, io, json, os, glob

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r:
        return zipfile.ZipFile(io.BytesIO(r.read()))

# 1. Fetch modern NuGet packages
z_azure = fetch("https://api.nuget.org/v3-flatcontainer/azure.identity/1.21.0/azure.identity.1.21.0.nupkg")
z_sql = fetch("https://api.nuget.org/v3-flatcontainer/microsoft.data.sqlclient/5.2.2/microsoft.data.sqlclient.5.2.2.nupkg")
z_sdc = fetch("https://api.nuget.org/v3-flatcontainer/system.drawing.common/8.0.0/system.drawing.common.8.0.0.nupkg")

azure_dll = z_azure.read("lib/net10.0/Azure.Identity.dll")
sql_dll = z_sql.read("runtimes/unix/lib/net8.0/Microsoft.Data.SqlClient.dll")
sdc_dll = z_sdc.read("lib/netstandard2.0/System.Drawing.Common.dll")

# 2. Update assemblies across /app
for root, dirs, files in os.walk("/app"):
    if "Azure.Identity.dll" in files:
        with open(os.path.join(root, "Azure.Identity.dll"), "wb") as f:
            f.write(azure_dll)
    if "Microsoft.Data.SqlClient.dll" in files:
        with open(os.path.join(root, "Microsoft.Data.SqlClient.dll"), "wb") as f:
            f.write(sql_dll)
    if "System.Drawing.Common.dll" in files:
        with open(os.path.join(root, "System.Drawing.Common.dll"), "wb") as f:
            f.write(sdc_dll)

# 3. Patch all .deps.json files
for p in sorted(glob.glob("/app/**/*.deps.json", recursive=True)):
    with open(p, "r", encoding="utf-8") as f:
        d = json.load(f)

    for target_name, target in d.get("targets", {}).items():
        # Azure.Identity
        old_az = [k for k in target if k.startswith("Azure.Identity/")]
        for k in old_az:
            entry = target.pop(k)
            entry["runtime"] = {
                "lib/net10.0/Azure.Identity.dll": {
                    "assemblyVersion": "1.21.0.0",
                    "fileVersion": "1.2100.26.11501"
                }
            }
            target["Azure.Identity/1.21.0"] = entry

        # Microsoft.Data.SqlClient
        old_sql = [k for k in target if k.startswith("Microsoft.Data.SqlClient/")]
        for k in old_sql:
            entry = target.pop(k)
            if "dependencies" in entry and "Azure.Identity" in entry["dependencies"]:
                entry["dependencies"]["Azure.Identity"] = "1.21.0"
            entry["runtimeTargets"] = {
                "runtimes/unix/lib/net8.0/Microsoft.Data.SqlClient.dll": {
                    "rid": "unix",
                    "assetType": "runtime",
                    "assemblyVersion": "5.0.0.0",
                    "fileVersion": "5.202.24263.2"
                }
            }
            target["Microsoft.Data.SqlClient/5.2.2"] = entry

        # System.Drawing.Common
        old_sdc = [k for k in target if k.startswith("System.Drawing.Common/")]
        for k in old_sdc:
            entry = target.pop(k)
            entry["runtime"] = {
                "lib/netstandard2.0/System.Drawing.Common.dll": {
                    "assemblyVersion": "8.0.0.0",
                    "fileVersion": "8.0.23.53105"
                }
            }
            entry.pop("runtimeTargets", None)
            target["System.Drawing.Common/8.0.0"] = entry

        # Update dependency references in other packages
        for pkg_entry in target.values():
            if isinstance(pkg_entry, dict) and "dependencies" in pkg_entry:
                deps = pkg_entry["dependencies"]
                if "Azure.Identity" in deps: deps["Azure.Identity"] = "1.21.0"
                if "Microsoft.Data.SqlClient" in deps: deps["Microsoft.Data.SqlClient"] = "5.2.2"
                if "System.Drawing.Common" in deps: deps["System.Drawing.Common"] = "8.0.0"

    # Libraries
    libs = d.get("libraries", {})
    for old_k in [k for k in libs if k.startswith("Azure.Identity/")]:
        le = libs.pop(old_k)
        le["path"] = "azure.identity/1.21.0"
        le["hashPath"] = "azure.identity.1.21.0.nupkg.sha512"
        libs["Azure.Identity/1.21.0"] = le

    for old_k in [k for k in libs if k.startswith("Microsoft.Data.SqlClient/")]:
        le = libs.pop(old_k)
        le["path"] = "microsoft.data.sqlclient/5.2.2"
        le["hashPath"] = "microsoft.data.sqlclient.5.2.2.nupkg.sha512"
        libs["Microsoft.Data.SqlClient/5.2.2"] = le

    for old_k in [k for k in libs if k.startswith("System.Drawing.Common/")]:
        le = libs.pop(old_k)
        le["path"] = "system.drawing.common/8.0.0"
        le["hashPath"] = "system.drawing.common.8.0.0.nupkg.sha512"
        libs["System.Drawing.Common/8.0.0"] = le

    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)

print("Stage 1: Successfully upgraded Azure.Identity, Microsoft.Data.SqlClient, and System.Drawing.Common")
EOF

# ==============================================================================
# Stage 2: Upgraded, secure Ubuntu 26.04 base environment
# ==============================================================================
FROM ubuntu:26.04 AS base-builder

ARG DEBIAN_FRONTEND=noninteractive

# Update system packages, apply security upgrades, and install runtime dependencies
RUN printf 'Package: snapd\nPin: release *\nPin-Priority: -10\n' > /etc/apt/preferences.d/nosnap.pref && \
    apt-get update && \
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
            intel-media-va-driver-non-free \
            libvpl2 libmfx-gen1.2 intel-opencl-icd libze-intel-gpu1; \
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

# OCI Standard Metadata Labels
LABEL org.opencontainers.image.title="FileFlows Real Image" \
      org.opencontainers.image.description="Hardened, debloated, production-ready multi-stage image built from upstream revenz/fileflows" \
      org.opencontainers.image.url="https://github.com/lusoris/fileflows-real-image" \
      org.opencontainers.image.source="https://github.com/lusoris/fileflows-real-image" \
      org.opencontainers.image.licenses="EUPL-1.2" \
      org.opencontainers.image.vendor="lusoris"

# Environment variables matching FileFlows configuration & container performance optimizations
ENV PATH=/dotnet:/dotnet/tools:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
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

# Ensure execution permissions on binaries and entrypoint
RUN chmod +x /usr/local/bin/docker /usr/local/bin/dovi_tool /app/docker-entrypoint.sh

# Expose web UI port
EXPOSE 5000/tcp

# Healthcheck validating FileFlows web interface
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f -s http://127.0.0.1:5000/initial-config || curl -f -s http://127.0.0.1:5000/ || exit 1

WORKDIR /app

ENTRYPOINT ["/app/docker-entrypoint.sh"]
