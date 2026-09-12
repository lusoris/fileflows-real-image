# Frequently Asked Questions (FAQ)

Answers to common questions regarding **FileFlows Real Image**, compatibility, security decisions, and operational best practices.

---

## Can I run the container with a read-only root filesystem (`read_only: true`)?

**No, not with the current upstream entrypoint.**

During our hardening benchmarks, we tested `read_only: true`. Upstream's `docker-entrypoint.sh` performs several runtime rootfs modifications on startup:

1. It executes `useradd` and `groupadd` to dynamically configure the user matching `PUID`/`PGID`.
2. It attempts `dpkg --configure -a`.
3. It writes startup diagnostic logs directly to `/app/startup.log`.

Running with `read_only: true` causes the entrypoint to fail immediately. Instead, we achieve equivalent runtime security by enforcing:

- `security_opt: [no-new-privileges:true]`
- `cap_drop: [ALL]` with minimal `cap_add: [CHOWN, SETUID, SETGID, DAC_OVERRIDE]`
- `init: true`

---

## Why retain FFmpeg shared libraries (`libavcodec62`, etc.) instead of static binaries?

Upstream FileFlows includes dynamic P/Invoke C# interop bindings and plugin components that dynamically load shared multimedia libraries (`libavcodec.so`, `libavformat.so`, `libswscale.so`, `libvpl.so`).

By replacing upstream's bloated `-dev` header packages with only the lean runtime shared libraries, we preserve 100% plugin compatibility while cutting over 120 MB of unnecessary build files.

---

## Will custom FileFlows C# scripts and plugins still work without the .NET SDK?

**Yes.**

In .NET 10, dynamic runtime script compilation (Roslyn compiler-as-a-service) used by FileFlows's script runner executes entirely within the `aspnetcore-runtime-10.0` environment using in-memory Roslyn assemblies. The external `dotnet-sdk` package (which contains project generators, CLI tools, and targeting packs) is never needed for runtime scripting.

---

## Why was `pebble` removed from the image?

Canonical's Rockcraft toolchain bakes the `pebble` service daemon into base images to facilitate process supervision in Charmed Kubernetes operators.

FileFlows is a standalone application that manages its own background workers and never invokes `pebble`. The binary bundled in upstream carries 6 Go standard library vulnerabilities (including Critical `CVE-2026-39821`). Removing `pebble` eliminates these CVEs with zero operational impact.

---

## Where should I report bugs?

- **Image build errors, CVEs, or docker packaging issues**: Report on [GitHub Issues](https://github.com/lusoris/fileflows-real-image/issues).
- **FileFlows UI, node communication, or transcoding flow bugs**: Report to upstream at [revenz/FileFlows](https://github.com/revenz/FileFlows).
