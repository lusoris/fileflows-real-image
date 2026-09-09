# Security Hardening & Vulnerability Management

This document details the security posture, vulnerability mitigations, and container isolation features engineered into **FileFlows Real Image**.

---

## 1. Zero Base CVE Guarantee

Upstream's official image (`revenz/fileflows:latest`) includes Canonical's Rockcraft `pebble` service daemon and unused Windows runtime assemblies that trigger critical scanner alerts.

| Vulnerability | Component | Severity | Real Image Status |
| :--- | :--- | :--- | :--- |
| `CVE-2026-39821` | Go stdlib / Pebble | **Critical** | **Resolved** (Pebble purged via rootfs squashing) |
| `CVE-2026-56862` | Go stdlib / Pebble | **High** | **Resolved** (Pebble purged) |
| `CVE-2026-56859` | Go stdlib / Pebble | **High** | **Resolved** (Pebble purged) |
| `CVE-2026-56853` | Go stdlib / Pebble | **High** | **Resolved** (Pebble purged) |
| `CVE-2026-46600` | Go stdlib / Pebble | **High** | **Resolved** (Pebble purged) |
| `CVE-2026-33818` | Go stdlib / Pebble | **High** | **Resolved** (Pebble purged) |
| `CVE-2021-24112` | System.Drawing.Common (Windows) | **Critical** | **Resolved** (Windows runtimes pruned) |
| `CVE-2024-0056` | Microsoft.Data.SqlClient (Windows) | **High** | **Resolved** (Windows runtimes pruned) |

Because FileFlows Real Image uses rootfs squashing (`FROM scratch COPY --from=base-builder / /`), deleted files are physically eliminated from the image layer history, guaranteeing scanners like Trivy and Grype find zero base CVEs.

---

## 2. Base Operating System Hardening

### Snap Pinning (`nosnap.pref`)
To prevent Canonical snapd daemon installation from pulling in large background daemons or kernel dependencies, `/etc/apt/preferences.d/nosnap.pref` pins `snapd` to priority `-10`:

```text
Package: snapd
Pin: release *
Pin-Priority: -10
```

### Attack Surface Minimization
- **Purged Utilities**: Removed `git`, `nano`, `gnupg`, and compiler tools (`gcc`, `g++`, `make`).
- **Stripped SUID/SGID Bits**: Executed `chmod a-s` recursively across all binaries to mitigate local privilege escalation risks.
- **Stripped Localization**: Removed non-English locales (`/usr/share/locale`) and manual pages (`/usr/share/man`, `/usr/share/doc`).

---

## 3. Container Isolation & Capabilities

While upstream's entrypoint requires brief root privileges to create the configured `PUID`/`PGID` account and set folder ownership, container permissions can be heavily restricted.

```yaml
services:
  fileflows:
    image: ghcr.io/lusoris/fileflows-real-image:latest
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETUID
      - SETGID
      - DAC_OVERRIDE
    init: true
```

### Why These Specific Capabilities?
- `cap_drop: [ALL]`: Strips all 40+ Linux capabilities, preventing raw socket manipulation, kernel module loading, and device node creation.
- `CHOWN`: Required by upstream's `docker-entrypoint.sh` to fix volume permissions.
- `SETUID` & `SETGID`: Required for the container entrypoint to transition execution to the unprivileged `PUID`/`PGID` user.
- `DAC_OVERRIDE`: Required to write to mounted host directories where permissions differ.
- `no-new-privileges: true`: Prevents processes from acquiring additional privileges via `setuid` or filesystem capabilities.

---

## 4. Signal Propagation & Zombie Reaping (`init: true`)

Media processing pipelines spawn external processes (e.g. `ffmpeg`, `ffprobe`, `mediainfo`). If a transcode job is cancelled or crashes, orphan child processes can become zombies if PID 1 does not reap them.

Adding `init: true` to your Docker Compose file instructs Docker to inject a lightweight init process (tini) as PID 1:
- Immediately reaps terminated transcode processes.
- Forwards `SIGTERM` and `SIGINT` signals cleanly, allowing FileFlows to flush databases and shutdown gracefully within seconds.
