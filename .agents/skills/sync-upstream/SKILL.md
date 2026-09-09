---
name: sync-upstream
description: Check upstream revenz/fileflows:latest for updates, compare image digests, bump version.txt, and verify build compatibility.
---

# /sync-upstream

Monitors and synchronizes FileFlows Real Image against upstream release builds from `revenz/fileflows:latest`.

## Invocation

```bash
/sync-upstream [--dry-run]
```

## Steps

1. **Query Upstream Digest**:
   Query Docker Hub API for the latest sha256 digest of `revenz/fileflows:latest`.
2. **Inspect Current Pinned Version**:
   Read `version.txt` and compare the upstream release version.
3. **Inspect Upstream Payload**:
   If a new version or digest is detected:
   - Check if upstream changed .NET runtime versions (`aspnetcore-runtime-10.0` vs older/newer).
   - Check if new NuGet packages introduce CVEs (inspect `/app/**/*.deps.json`).
   - Verify `docker-entrypoint.sh` startup script still contains known driver setup commands neutralized by `sed`.
4. **Update Pinned Version**:
   Update `version.txt` and document the new version in `README.md` and `docs/`.
5. **Run Local Smoke Test**:
   Build the `:latest` flavor and execute `pytest tests/test_image.py`.
6. **Verify Drift**:
   Ensure `Dockerfile.optimized` is synchronized with `Dockerfile`.
