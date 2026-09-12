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

## Why is `libgdiplus` not installed, leaving System.Drawing non-functional?

**Because nothing calls it, and installing it would add eight image parsers to a zero-CVE image.**

`System.Drawing.Common` is present in the image, and any attempt to use it throws
`TypeInitializationException: The type initializer for 'Gdip' threw an exception`, because the
native GDI+ shim `libgdiplus` is absent. That is deliberate, and it matches upstream: upstream
`revenz/fileflows:latest` ships no `runtimes/unix` asset for the package at all, so a Linux-capable
System.Drawing has never existed in a FileFlows container.

The assembly is not an imaging dependency. It arrives as a seven-hop transitive artifact of the
SQL Server data-access stack:

```text
FileFlows.FlowRunner -> FileFlows.ServerShared -> NPoco.SqlServer -> Microsoft.Data.SqlClient
  -> System.Configuration.ConfigurationManager -> System.Security.Permissions
  -> System.Windows.Extensions -> System.Drawing.Common
```

A metadata scan of all 319 assemblies in `/app` finds **zero** references to `System.Drawing` from
any of the 50 `FileFlows*.dll` files. FileFlows does all of its imaging with
[SixLabors.ImageSharp](https://github.com/SixLabors/ImageSharp), which is fully managed and needs no
native library. Only one physical copy of the assembly exists on disk, under `FlowRunner`; the
server and agent manifests do not reference it at all.

Installing `libgdiplus` does work — it is one `apt` line, and with it the shipped assembly encodes a
PNG correctly. It is omitted because the cost points the wrong way: nine packages, eight of which are
third-party C image codecs (`libtiff6`, `libjpeg-turbo8`, `libjpeg8`, `libgif7`, `libexif12`,
`libjbig0`, `liblerc4`, `libdeflate0`), drawn from Ubuntu *universe* rather than *main*. Those are
among the most vulnerability-prone parsers in the archive, and adding them to an image whose headline
guarantee is zero CRITICAL/HIGH findings buys a capability with no caller.

If a plugin ever fails with the `Gdip` error above, that is the signal to revisit this: the fix is a
single package, and the reasoning here is what should be re-examined, not the symptom.

## Where should I report bugs?

- **Image build errors, CVEs, or docker packaging issues**: Report on [GitHub Issues](https://github.com/lusoris/fileflows-real-image/issues).
- **FileFlows UI, node communication, or transcoding flow bugs**: Report to upstream at [revenz/FileFlows](https://github.com/revenz/FileFlows).
