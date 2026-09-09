---
name: security-audit
description: Run container vulnerability scans, verify Zero-CVE base hardening, check Pebble purge, and validate patched NuGet dependencies.
---

# /security-audit

Performs deep vulnerability scanning and compliance checks against FileFlows Real Image container artifacts.

## Invocation

```bash
/security-audit [image_tag]
```

Default: `ghcr.io/lusoris/fileflows-real-image:latest`

## Verification Checks

1. **Zero Base CVE Invariant**:
   - Run Trivy vulnerability scanner on image filesystem:
     ```bash
     trivy image --severity HIGH,CRITICAL --ignore-unfixed ghcr.io/lusoris/fileflows-real-image:latest
     ```
   - Must return 0 Critical and 0 High vulnerabilities.
2. **Pebble Daemon Purge**:
   - Ensure `/usr/bin/pebble`, `/var/lib/pebble`, and `/etc/pebble` do not exist in the rootfs:
     ```bash
     docker run --rm ghcr.io/lusoris/fileflows-real-image:latest test ! -e /usr/bin/pebble
     ```
3. **NuGet Vulnerability Mitigation**:
   - Verify that patched assemblies in `/app` match secure versions:
     - `Azure.Identity` >= 1.21.0 (remediates CVE-2023-36414, CVE-2024-29992, CVE-2024-35255)
     - `Microsoft.Data.SqlClient` >= 5.2.2 (remediates CVE-2024-0056)
     - `System.Drawing.Common` >= 8.0.0 (remediates CVE-2021-24112)
4. **Secret Scanning**:
   - Verify no credentials or API tokens leaked in image layers:
     ```bash
     gitleaks detect --verbose --config .gitleaks.toml
     ```
