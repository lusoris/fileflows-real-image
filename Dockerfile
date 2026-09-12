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

# Tolerantly stage optional upstream utility binaries if present
RUN mkdir -p /extra-bin && \
    for bin in docker dovi_tool; do \
        if [ -f "/usr/local/bin/${bin}" ]; then \
            cp -a "/usr/local/bin/${bin}" /extra-bin/; \
        fi; \
    done

# Dynamic Semantic NuGet Vulnerability Remediator:
# - Inspects active versions across all /app/**/*.deps.json files
# - If upstream has already upgraded to or beyond safe minimum versions, preserves upstream (no downgrade)
# - If packages are vulnerable or older than safe minimums, upgrades assembly and patches .deps.json
# - Resolves CVE-2023-36414, CVE-2024-29992, CVE-2024-35255 (Azure.Identity 1.3.0 -> 1.11.4)
# - Resolves CVE-2024-0056 (Microsoft.Data.SqlClient 3.0.0 -> 3.1.5)
# - Resolves CVE-2021-24112 (System.Drawing.Common 4.7.0 -> 4.7.2)
# - Resolves CVE-2025-6965 (SQLitePCLRaw.lib.e_sqlite3 2.1.11 -> 2.1.12, native per-RID)
RUN echo "IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwoiIiIKRHluYW1pYyBTZW1hbnRpYyBOdUdldCBWdWxuZXJhYmlsaXR5IFJlbWVkaWF0b3IgZm9yIEZpbGVGbG93cyBSZWFsIEltYWdlLgoKLSBJbnNwZWN0cyBhY3RpdmUgdmVyc2lvbnMgYWNyb3NzIGFsbCAvYXBwLyoqLyouZGVwcy5qc29uIGZpbGVzLgotIFJlbWVkaWF0ZXMgb25seSB3aGF0IHRoZSBhZHZpc29yaWVzIGFjdHVhbGx5IHJlcXVpcmUsIHNvIGFuIHVwc3RyZWFtIGFzc2VtYmx5IHRoYXQgaXMKICBhbHJlYWR5IHBhdGNoZWQgaXMgbmV2ZXIgcmVwbGFjZWQ6IG1pbl92ZXJzaW9uIGlzIHRoZSBwdWJsaXNoZWQgZml4ZWQgdmVyc2lvbiwgbm90IHRoZQogIGxhdGVzdCByZWxlYXNlLiB0YXJnZXRfdmVyc2lvbl9zdHIgaXMgd2hhdCBnZXRzIGluc3RhbGxlZCB3aGVuIGludGVydmVudGlvbiBpcyBuZWVkZWQuCi0gRmFpbHMgY2xvc2VkOiBhIG1hbmlmZXN0IGlzIG9ubHkgcmV3cml0dGVuIG9uY2UgdGhlIHJlcGxhY2VtZW50IGFzc2VtYmx5IGlzIG9uIGRpc2suCi0gUmVzb2x2ZXMgQ1ZFLTIwMjMtMzY0MTQsIENWRS0yMDI0LTI5OTkyLCBDVkUtMjAyNC0zNTI1NSAoQXp1cmUuSWRlbnRpdHkgMS4zLjAgLT4gMS4xMS40KQotIFJlc29sdmVzIENWRS0yMDI0LTAwNTYgKE1pY3Jvc29mdC5EYXRhLlNxbENsaWVudCAzLjAuMCAtPiAzLjEuNSkKLSBSZXNvbHZlcyBDVkUtMjAyMS0yNDExMiAoU3lzdGVtLkRyYXdpbmcuQ29tbW9uIDQuNy4wIC0+IDQuNy4yKQotIFJlc29sdmVzIENWRS0yMDI1LTY5NjUgKFNRTGl0ZVBDTFJhdy5saWIuZV9zcWxpdGUzIDIuMS4xMSAtPiAyLjEuMTIsIG5hdGl2ZSBwZXItUklEKQoiIiIKCmltcG9ydCBnbG9iCmltcG9ydCBpbwppbXBvcnQganNvbgppbXBvcnQgb3MKaW1wb3J0IHJlCmltcG9ydCB1cmxsaWIucmVxdWVzdAppbXBvcnQgemlwZmlsZQoKTlVHRVRfVElNRU9VVF9TRUNPTkRTID0gNjAKCiMgQXp1cmUuSWRlbnRpdHkgMS4xMS40IG5lZWRzIGEgbmV3ZXIgZGVwZW5kZW5jeSBzZXQgdGhhbiB1cHN0cmVhbSBzaGlwcywgYW5kIHVwZ3JhZGluZyB0aGUKIyBhc3NlbWJseSB3aXRob3V0IHRoZW0gbGVhdmVzIGl0IHVubG9hZGFibGUgKCJDb3VsZCBub3QgbG9hZCBBenVyZS5Db3JlLCBWZXJzaW9uPTEuMzguMC4wIikuCiMgUmVzb2x2ZWQgd2l0aCBgZG90bmV0IHB1Ymxpc2hgIGZvciBuZXQxMC4wIGFuZCByZWR1Y2VkIHRvIHdoYXQgL2FwcCBkb2VzIG5vdCBhbHJlYWR5CiMgc2F0aXNmeTogTWljcm9zb2Z0LklkZW50aXR5TW9kZWwuQWJzdHJhY3Rpb25zICg4LjE5LjEpIGFuZAojIFN5c3RlbS5TZWN1cml0eS5DcnlwdG9ncmFwaHkuUHJvdGVjdGVkRGF0YSAoNC43LjApIGFyZSBhbHJlYWR5IG5ldyBlbm91Z2guCkFaVVJFX0lERU5USVRZX0NMT1NVUkUgPSBbCiAgICB7Im5hbWUiOiAiQXp1cmUuQ29yZSIsICJ2ZXJzaW9uIjogIjEuMzguMCIsICJhc3NldCI6ICJsaWIvbmV0Ni4wL0F6dXJlLkNvcmUuZGxsIn0sCiAgICB7Im5hbWUiOiAiTWljcm9zb2Z0LkJjbC5Bc3luY0ludGVyZmFjZXMiLCAidmVyc2lvbiI6ICIxLjEuMSIsCiAgICAgImFzc2V0IjogImxpYi9uZXRzdGFuZGFyZDIuMS9NaWNyb3NvZnQuQmNsLkFzeW5jSW50ZXJmYWNlcy5kbGwifSwKICAgIHsibmFtZSI6ICJNaWNyb3NvZnQuSWRlbnRpdHkuQ2xpZW50IiwgInZlcnNpb24iOiAiNC42MS4zIiwKICAgICAiYXNzZXQiOiAibGliL25ldDYuMC9NaWNyb3NvZnQuSWRlbnRpdHkuQ2xpZW50LmRsbCJ9LAogICAgeyJuYW1lIjogIk1pY3Jvc29mdC5JZGVudGl0eS5DbGllbnQuRXh0ZW5zaW9ucy5Nc2FsIiwgInZlcnNpb24iOiAiNC42MS4zIiwKICAgICAiYXNzZXQiOiAibGliL25ldDYuMC9NaWNyb3NvZnQuSWRlbnRpdHkuQ2xpZW50LkV4dGVuc2lvbnMuTXNhbC5kbGwifSwKICAgIHsibmFtZSI6ICJTeXN0ZW0uQ2xpZW50TW9kZWwiLCAidmVyc2lvbiI6ICIxLjAuMCIsICJhc3NldCI6ICJsaWIvbmV0Ni4wL1N5c3RlbS5DbGllbnRNb2RlbC5kbGwifSwKICAgIHsibmFtZSI6ICJTeXN0ZW0uTWVtb3J5LkRhdGEiLCAidmVyc2lvbiI6ICIxLjAuMiIsICJhc3NldCI6ICJsaWIvbmV0c3RhbmRhcmQyLjAvU3lzdGVtLk1lbW9yeS5EYXRhLmRsbCJ9LApdCgpUQVJHRVRfUEFDS0FHRVMgPSB7CiAgICAiQXp1cmUuSWRlbnRpdHkiOiB7CiAgICAgICAgIyBDVkUtMjAyMy0zNjQxNCAtPiAxLjEwLjIsIENWRS0yMDI0LTI5OTkyIC0+IDEuMTEuMCwgQ1ZFLTIwMjQtMzUyNTUgLT4gMS4xMS40CiAgICAgICAgImFkdmlzb3J5X2ZpeGVkX3ZlcnNpb25zIjogWygxLCAxMSwgNCldLAogICAgICAgICMgSW5zdGFsbCB0aGUgYWR2aXNvcnkncyBmaXhlZCB2ZXJzaW9uLCBub3QgdGhlIG5ld2VzdCByZWxlYXNlOiB1cHN0cmVhbSBzaGlwcwogICAgICAgICMgMS4zLjAsIGFuZCAxLjExLjQga2VlcHMgdGhlIHNhbWUgc2luZ2xlIG5ldHN0YW5kYXJkMi4wIGFzc2V0IGl0IGFscmVhZHkKICAgICAgICAjIHJlZmVyZW5jZXMsIHNvIG9ubHkgdGhlIHZlcnNpb24gbWV0YWRhdGEgY2hhbmdlcy4KICAgICAgICAidGFyZ2V0X3ZlcnNpb25fc3RyIjogIjEuMTEuNCIsCiAgICAgICAgIm51cGtnX3VybCI6ICJodHRwczovL2FwaS5udWdldC5vcmcvdjMtZmxhdGNvbnRhaW5lci9henVyZS5pZGVudGl0eS8xLjExLjQvYXp1cmUuaWRlbnRpdHkuMS4xMS40Lm51cGtnIiwKICAgICAgICAiZGxsX3JlbF9wYXRoIjogImxpYi9uZXRzdGFuZGFyZDIuMC9BenVyZS5JZGVudGl0eS5kbGwiLAogICAgICAgICJkbGxfbmFtZSI6ICJBenVyZS5JZGVudGl0eS5kbGwiLAogICAgICAgICMgQXp1cmUgU0RLIHN0YW1wcyBhc3NlbWJseVZlcnNpb24gYXMgbWFqb3IubWlub3IuMC4wLCBzbyAxLjMuMC4wIC0+IDEuMTEuMC4wLgogICAgICAgICJhc3NlbWJseV92ZXJzaW9uIjogIjEuMTEuMC4wIiwKICAgICAgICAiY2xvc3VyZSI6IEFaVVJFX0lERU5USVRZX0NMT1NVUkUsCiAgICB9LAogICAgIk1pY3Jvc29mdC5EYXRhLlNxbENsaWVudCI6IHsKICAgICAgICAjIENWRS0yMDI0LTAwNTYgd2FzIGZpeGVkIHNlcGFyYXRlbHkgb24gZWFjaCBtYWludGFpbmVkIGJyYW5jaCwgYW5kCiAgICAgICAgIyBDVkUtMjAyMi00MTA2NCBvbiB0aGUgMS54LzIueCBicmFuY2hlcy4KICAgICAgICAiYWR2aXNvcnlfZml4ZWRfdmVyc2lvbnMiOiBbKDEsIDEsIDQpLCAoMiwgMSwgNyksICgzLCAxLCA1KSwgKDQsIDAsIDUpLCAoNSwgMSwgMyldLAogICAgICAgICMgMy4xLjUgaXMgdGhlIGZpeCBvbiB1cHN0cmVhbSdzIG93biAzLnggYnJhbmNoLiBTdGF5aW5nIG9uIDMueCBhdm9pZHMgdGhlIDQuMAogICAgICAgICMgYnJlYWtpbmcgY2hhbmdlIHRoYXQgZmxpcHBlZCB0aGUgZGVmYXVsdCBjb25uZWN0aW9uIHN0cmluZyB0byBFbmNyeXB0PXRydWUuCiAgICAgICAgInRhcmdldF92ZXJzaW9uX3N0ciI6ICIzLjEuNSIsCiAgICAgICAgIm51cGtnX3VybCI6ICJodHRwczovL2FwaS5udWdldC5vcmcvdjMtZmxhdGNvbnRhaW5lci9taWNyb3NvZnQuZGF0YS5zcWxjbGllbnQvMy4xLjUvbWljcm9zb2Z0LmRhdGEuc3FsY2xpZW50LjMuMS41Lm51cGtnIiwKICAgICAgICAiZGxsX3JlbF9wYXRoIjogInJ1bnRpbWVzL3VuaXgvbGliL25ldGNvcmVhcHAzLjEvTWljcm9zb2Z0LkRhdGEuU3FsQ2xpZW50LmRsbCIsCiAgICAgICAgImRsbF9uYW1lIjogIk1pY3Jvc29mdC5EYXRhLlNxbENsaWVudC5kbGwiLAogICAgICAgICMgVW5jaGFuZ2VkIGFjcm9zcyB0aGUgMy54IGJyYW5jaDsgdXBzdHJlYW0gYWxyZWFkeSByZWNvcmRzIDMuMC4wLjAuCiAgICAgICAgImFzc2VtYmx5X3ZlcnNpb24iOiBOb25lLAogICAgfSwKICAgICJTUUxpdGVQQ0xSYXcubGliLmVfc3FsaXRlMyI6IHsKICAgICAgICAjIENWRS0yMDI1LTY5NjU6IHRoZSBidW5kbGVkIFNRTGl0ZSBidWlsZCBpcyB2dWxuZXJhYmxlIHVwIHRvIGFuZCBpbmNsdWRpbmcKICAgICAgICAjIDIuMS4xMSwgc28gMi4xLjEyIGlzIHRoZSBtaW5pbWFsIGZpeCBvbiB0aGF0IGJyYW5jaC4KICAgICAgICAiYWR2aXNvcnlfZml4ZWRfdmVyc2lvbnMiOiBbKDIsIDEsIDEyKV0sCiAgICAgICAgInRhcmdldF92ZXJzaW9uX3N0ciI6ICIyLjEuMTIiLAogICAgICAgICJudXBrZ191cmwiOiAiaHR0cHM6Ly9hcGkubnVnZXQub3JnL3YzLWZsYXRjb250YWluZXIvc3FsaXRlcGNscmF3LmxpYi5lX3NxbGl0ZTMvMi4xLjEyL3NxbGl0ZXBjbHJhdy5saWIuZV9zcWxpdGUzLjIuMS4xMi5udXBrZyIsCiAgICAgICAgIyBBIG5hdGl2ZSBwYWNrYWdlOiBldmVyeSBSSUQgc2hpcHMgaXRzIG93biBiaW5hcnksIHNvIGVhY2ggb24tZGlzayBjb3B5IGlzCiAgICAgICAgIyByZXBsYWNlZCB3aXRoIHRoZSBhc3NldCBwdWJsaXNoZWQgZm9yIHRoYXQgc2FtZSBSSUQgcmF0aGVyIHRoYW4gb25lIGNob3NlbiBidWlsZC4KICAgICAgICAiYXNzZXRfa2luZCI6ICJuYXRpdmUiLAogICAgICAgICJkbGxfcmVsX3BhdGgiOiAicnVudGltZXMvbGludXgteDY0L25hdGl2ZS9saWJlX3NxbGl0ZTMuc28iLAogICAgICAgICJkbGxfbmFtZSI6ICJsaWJlX3NxbGl0ZTMuc28iLAogICAgICAgICJhc3NlbWJseV92ZXJzaW9uIjogTm9uZSwKICAgIH0sCiAgICAiU3lzdGVtLkRyYXdpbmcuQ29tbW9uIjogewogICAgICAgICMgQ1ZFLTIwMjEtMjQxMTIgLT4gNC43LjIgb24gdGhlIDQueCBicmFuY2gsIDUuMC4zIG9uIHRoZSA1LnggYnJhbmNoLgogICAgICAgICJhZHZpc29yeV9maXhlZF92ZXJzaW9ucyI6IFsoNCwgNywgMiksICg1LCAwLCAzKV0sCiAgICAgICAgIyA0LjcuMiBpcyB0aGUgZml4IG9uIHVwc3RyZWFtJ3MgNC43LnggYnJhbmNoLiA2LjArIGRyb3BwZWQgVW5peCBzdXBwb3J0IGFuZAogICAgICAgICMgOC4wLjAgc2hpcHMgbm8gcnVudGltZXMvdW5peCBhc3NldCBhdCBhbGwsIHNvIHVwZ3JhZGluZyB0aGF0IGZhciB3b3VsZCB0cmFkZSBhCiAgICAgICAgIyB3b3JraW5nIExpbnV4IGltcGxlbWVudGF0aW9uIGZvciBhIFdpbmRvd3Mtb25seSBvbmUuCiAgICAgICAgInRhcmdldF92ZXJzaW9uX3N0ciI6ICI0LjcuMiIsCiAgICAgICAgIm51cGtnX3VybCI6ICJodHRwczovL2FwaS5udWdldC5vcmcvdjMtZmxhdGNvbnRhaW5lci9zeXN0ZW0uZHJhd2luZy5jb21tb24vNC43LjIvc3lzdGVtLmRyYXdpbmcuY29tbW9uLjQuNy4yLm51cGtnIiwKICAgICAgICAiZGxsX3JlbF9wYXRoIjogInJ1bnRpbWVzL3VuaXgvbGliL25ldGNvcmVhcHAzLjAvU3lzdGVtLkRyYXdpbmcuQ29tbW9uLmRsbCIsCiAgICAgICAgImRsbF9uYW1lIjogIlN5c3RlbS5EcmF3aW5nLkNvbW1vbi5kbGwiLAogICAgICAgICMgVW5jaGFuZ2VkIGFjcm9zcyA0LjcueDsgdXBzdHJlYW0gcmVjb3JkcyA0LjAuMC4xIC8gNC4wLjIuMCBwZXIgYXNzZXQuCiAgICAgICAgImFzc2VtYmx5X3ZlcnNpb24iOiBOb25lLAogICAgfSwKfQoKCmRlZiBwYXJzZV92ZXJzaW9uKHZfc3RyOiBzdHIpIC0+IHR1cGxlOgogICAgIiIiUGFyc2Ugc2VtYW50aWMgdmVyc2lvbiBzdHJpbmcgaW50byBhIGNvbXBhcmFibGUgdHVwbGUgb2YgaW50ZWdlcnMuIiIiCiAgICBwYXJ0cyA9IHJlLmZpbmRhbGwociJcZCsiLCB2X3N0ci5zcGxpdCgiLSIpWzBdLnNwbGl0KCIrIilbMF0pCiAgICByZXR1cm4gdHVwbGUobWFwKGludCwgcGFydHMpKSBpZiBwYXJ0cyBlbHNlICgwLCkKCgpkZWYgYXBwbGljYWJsZV9maXgodmVyc2lvbjogdHVwbGUsIGZpeGVkX3ZlcnNpb25zOiBsaXN0KSAtPiB0dXBsZToKICAgICIiIlJldHVybiB0aGUgYWR2aXNvcnkgZml4IHRoYXQgZ292ZXJucyBgdmVyc2lvbmAsIG9yIE5vbmUgaWYgaXQgaXMgdW5hZmZlY3RlZC4KCiAgICBBZHZpc29yaWVzIGZvciB0aGVzZSBwYWNrYWdlcyBhcmUgZml4ZWQgaW5kZXBlbmRlbnRseSBvbiBlYWNoIG1haW50YWluZWQgYnJhbmNoLCBzbwogICAgYSBzaW5nbGUgIm1pbmltdW0gc2FmZSB2ZXJzaW9uIiB3b3VsZCBlaXRoZXIgbWlzcyBhIHZ1bG5lcmFibGUgbmV3ZXIgYnJhbmNoIG9yCiAgICBjb25kZW1uIGFuIGFscmVhZHktcGF0Y2hlZCBvbGRlciBvbmUuIEEgdmVyc2lvbiBpcyBqdWRnZWQgYWdhaW5zdCB0aGUgZml4IHB1Ymxpc2hlZAogICAgZm9yIGl0cyBvd24gbWFqb3IgbGluZTsgYSBtYWpvciBsaW5lIG5vIGFkdmlzb3J5IGV2ZXIgdG91Y2hlZCBpcyBhZmZlY3RlZCBvbmx5IGlmIGl0CiAgICBwcmVkYXRlcyBldmVyeSBmaXhlZCBicmFuY2guCiAgICAiIiIKICAgIHNhbWVfYnJhbmNoID0gW2YgZm9yIGYgaW4gZml4ZWRfdmVyc2lvbnMgaWYgZlswXSA9PSB2ZXJzaW9uWzBdXQogICAgaWYgc2FtZV9icmFuY2g6CiAgICAgICAgcmVxdWlyZWQgPSBtYXgoc2FtZV9icmFuY2gpCiAgICAgICAgcmV0dXJuIHJlcXVpcmVkIGlmIHZlcnNpb24gPCByZXF1aXJlZCBlbHNlIE5vbmUKICAgIG9sZGVzdCA9IG1pbihmaXhlZF92ZXJzaW9ucykKICAgIHJldHVybiBvbGRlc3QgaWYgdmVyc2lvbiA8IG9sZGVzdCBlbHNlIE5vbmUKCgpkZWYgZmluZF9kZXBzX2ZpbGVzKGFwcF9yb290OiBzdHIpIC0+IGxpc3Q6CiAgICAiIiJSZXR1cm4gZXZlcnkgLmRlcHMuanNvbiB1bmRlciBhcHBfcm9vdCwgaW5jbHVkaW5nIG9uZXMgZGlyZWN0bHkgaW4gaXQuIiIiCiAgICByb290ID0gYXBwX3Jvb3QucnN0cmlwKCIvIikgb3IgIi8iCiAgICByZXR1cm4gc29ydGVkKHNldChnbG9iLmdsb2IoZiJ7Z2xvYi5lc2NhcGUocm9vdCl9LyoqLyouZGVwcy5qc29uIiwgcmVjdXJzaXZlPVRydWUpKSkKCgpkZWYgcmVhZF9maWxlX3ZlcnNpb24oZGxsX2J5dGVzOiBieXRlcykgLT4gc3RyOgogICAgIiIiRXh0cmFjdCB0aGUgV2luMzIgRmlsZVZlcnNpb24gZnJvbSBhIFBFJ3MgVlNfRklYRURGSUxFSU5GTyBibG9jaywgaWYgcHJlc2VudC4iIiIKICAgIG1hcmtlciA9IGIiXHhiZFx4MDRceGVmXHhmZSIgICMgVlNfRklYRURGSUxFSU5GTyBkd1NpZ25hdHVyZSAweEZFRUYwNEJELCBsaXR0bGUtZW5kaWFuCiAgICBvZmZzZXQgPSBkbGxfYnl0ZXMuZmluZChtYXJrZXIpCiAgICBpZiBvZmZzZXQgPCAwIG9yIG9mZnNldCArIDE2ID4gbGVuKGRsbF9ieXRlcyk6CiAgICAgICAgcmV0dXJuICIiCgogICAgZGVmIF91MzIoYXQpOgogICAgICAgIHJldHVybiBpbnQuZnJvbV9ieXRlcyhkbGxfYnl0ZXNbYXQ6YXQgKyA0XSwgImxpdHRsZSIpCgogICAgbXMsIGxzID0gX3UzMihvZmZzZXQgKyA4KSwgX3UzMihvZmZzZXQgKyAxMikKICAgIHJldHVybiBmInttcyA+PiAxNn0ue21zICYgMHhGRkZGfS57bHMgPj4gMTZ9LntscyAmIDB4RkZGRn0iCgoKZGVmIGZldGNoX251cGtnKHVybDogc3RyKSAtPiBieXRlczoKICAgICIiIkRvd25sb2FkIGEgTnVHZXQgcGFja2FnZSwgdmVyaWZ5aW5nIHRoZSByZXNwb25zZSBiZWZvcmUgaXQgaXMgb3BlbmVkLiIiIgogICAgcmVxID0gdXJsbGliLnJlcXVlc3QuUmVxdWVzdCh1cmwsIGhlYWRlcnM9eyJVc2VyLUFnZW50IjogIkZpbGVGbG93cy1SZWFsLUltYWdlLzEuMCJ9KQogICAgd2l0aCB1cmxsaWIucmVxdWVzdC51cmxvcGVuKHJlcSwgdGltZW91dD1OVUdFVF9USU1FT1VUX1NFQ09ORFMpIGFzIHJlc3A6CiAgICAgICAgc3RhdHVzID0gZ2V0YXR0cihyZXNwLCAic3RhdHVzIiwgTm9uZSkKICAgICAgICBpZiBzdGF0dXMgaXMgbm90IE5vbmUgYW5kIHN0YXR1cyAhPSAyMDA6CiAgICAgICAgICAgIHJhaXNlIFJ1bnRpbWVFcnJvcihmIk51R2V0IHJldHVybmVkIEhUVFAge3N0YXR1c30gZm9yIHt1cmx9IikKICAgICAgICBwYXlsb2FkID0gcmVzcC5yZWFkKCkKCiAgICBpZiBub3QgcGF5bG9hZDoKICAgICAgICByYWlzZSBSdW50aW1lRXJyb3IoZiJOdUdldCByZXR1cm5lZCBhbiBlbXB0eSByZXNwb25zZSBib2R5IGZvciB7dXJsfSIpCiAgICByZXR1cm4gcGF5bG9hZAoKCmRlZiBmZXRjaF9udXBrZ19kbGwodXJsOiBzdHIsIGRsbF9yZWxfcGF0aDogc3RyKSAtPiBieXRlczoKICAgICIiIkRvd25sb2FkIGEgTnVHZXQgcGFja2FnZSBhbmQgZXh0cmFjdCBvbmUgYXNzZW1ibHksIHZlcmlmeWluZyBldmVyeSBzdGVwLiIiIgogICAgd2l0aCB6aXBmaWxlLlppcEZpbGUoaW8uQnl0ZXNJTyhmZXRjaF9udXBrZyh1cmwpKSkgYXMgYXJjaGl2ZToKICAgICAgICBpZiBkbGxfcmVsX3BhdGggbm90IGluIGFyY2hpdmUubmFtZWxpc3QoKToKICAgICAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKGYiQXNzZXQgJ3tkbGxfcmVsX3BhdGh9JyBpcyBhYnNlbnQgZnJvbSB7dXJsfSIpCiAgICAgICAgZGxsX2J5dGVzID0gYXJjaGl2ZS5yZWFkKGRsbF9yZWxfcGF0aCkKCiAgICBpZiBub3QgZGxsX2J5dGVzOgogICAgICAgIHJhaXNlIFJ1bnRpbWVFcnJvcihmIkFzc2V0ICd7ZGxsX3JlbF9wYXRofScgaXMgZW1wdHkgaW4ge3VybH0iKQogICAgcmV0dXJuIGRsbF9ieXRlcwoKCmRlZiByZXBsYWNlX3JpZF9hc3NldHMoYXBwX3Jvb3Q6IHN0ciwgcGFja2FnZTogYnl0ZXMsIGFzc2V0X25hbWU6IHN0cikgLT4gaW50OgogICAgIiIiUmVwbGFjZSBlYWNoIHJ1bnRpbWVzLzxyaWQ+Ly4uLiBjb3B5IG9mIGFzc2V0X25hbWUgd2l0aCB0aGUgcGFja2FnZSdzIG93biBidWlsZC4KCiAgICBOYXRpdmUgcGFja2FnZXMgc2hpcCBhIGRpc3RpbmN0IGJpbmFyeSBwZXIgcnVudGltZSBpZGVudGlmaWVyLCBzbyB3cml0aW5nIG9uZQogICAgY2hvc2VuIGJ1aWxkIG92ZXIgYWxsIG9mIHRoZW0gd291bGQgcHV0LCBzYXksIGFuIHg2NCBsaWJyYXJ5IGluIHRoZSBhcm02NCBzbG90LgogICAgIiIiCiAgICB3aXRoIHppcGZpbGUuWmlwRmlsZShpby5CeXRlc0lPKHBhY2thZ2UpKSBhcyBhcmNoaXZlOgogICAgICAgIGFzc2V0cyA9IHsKICAgICAgICAgICAgbmFtZTogYXJjaGl2ZS5yZWFkKG5hbWUpCiAgICAgICAgICAgIGZvciBuYW1lIGluIGFyY2hpdmUubmFtZWxpc3QoKQogICAgICAgICAgICBpZiBuYW1lLnN0YXJ0c3dpdGgoInJ1bnRpbWVzLyIpIGFuZCBuYW1lLmVuZHN3aXRoKCIvIiArIGFzc2V0X25hbWUpCiAgICAgICAgfQogICAgaWYgbm90IGFzc2V0czoKICAgICAgICByYWlzZSBSdW50aW1lRXJyb3IoZiJQYWNrYWdlIGNvbnRhaW5zIG5vIHJ1bnRpbWVzLyoqL3thc3NldF9uYW1lfSBhc3NldHMiKQoKICAgIHJlcGxhY2VkX2NvdW50ID0gMAogICAgZm9yIHJvb3QsIF8sIGZpbGVzIGluIG9zLndhbGsoYXBwX3Jvb3QpOgogICAgICAgIGlmIGFzc2V0X25hbWUgbm90IGluIGZpbGVzOgogICAgICAgICAgICBjb250aW51ZQogICAgICAgIHBhdGggPSBvcy5wYXRoLmpvaW4ocm9vdCwgYXNzZXRfbmFtZSkKICAgICAgICBtYXJrZXIgPSBvcy5zZXAgKyAicnVudGltZXMiICsgb3Muc2VwCiAgICAgICAgaWYgbWFya2VyIG5vdCBpbiBwYXRoOgogICAgICAgICAgICBjb250aW51ZQogICAgICAgIHJlbGF0aXZlID0gcGF0aFtwYXRoLnJpbmRleChtYXJrZXIpICsgMTpdLnJlcGxhY2Uob3Muc2VwLCAiLyIpCiAgICAgICAgaWYgcmVsYXRpdmUgaW4gYXNzZXRzOgogICAgICAgICAgICB3aXRoIG9wZW4ocGF0aCwgIndiIikgYXMgaGFuZGxlOgogICAgICAgICAgICAgICAgaGFuZGxlLndyaXRlKGFzc2V0c1tyZWxhdGl2ZV0pCiAgICAgICAgICAgIHJlcGxhY2VkX2NvdW50ICs9IDEKICAgIHJldHVybiByZXBsYWNlZF9jb3VudAoKCmRlZiBudWdldF91cmwobmFtZTogc3RyLCB2ZXJzaW9uOiBzdHIpIC0+IHN0cjoKICAgICIiIkZsYXQtY29udGFpbmVyIFVSTCBmb3Igb25lIHBhY2thZ2UgdmVyc2lvbi4iIiIKICAgIGxvd2VyID0gbmFtZS5sb3dlcigpCiAgICByZXR1cm4gZiJodHRwczovL2FwaS5udWdldC5vcmcvdjMtZmxhdGNvbnRhaW5lci97bG93ZXJ9L3t2ZXJzaW9ufS97bG93ZXJ9Lnt2ZXJzaW9ufS5udXBrZyIKCgpkZWYgaG9zdF9kaXJlY3RvcmllcyhhcHBfcm9vdDogc3RyLCBkbGxfbmFtZTogc3RyKSAtPiBsaXN0OgogICAgIiIiRGlyZWN0b3JpZXMgaG9sZGluZyBkbGxfbmFtZTsgYSBkZXBlbmRlbmN5J3MgYXNzZW1ibHkgaGFzIHRvIHNpdCBhbG9uZ3NpZGUgaXQuIiIiCiAgICByZXR1cm4gc29ydGVkKHtyb290IGZvciByb290LCBfLCBmaWxlcyBpbiBvcy53YWxrKGFwcF9yb290KSBpZiBkbGxfbmFtZSBpbiBmaWxlc30pCgoKZGVmIHJlZmVyZW5jZXNfcGFja2FnZShwYXRoOiBzdHIsIHBrZ19uYW1lOiBzdHIpIC0+IGJvb2w6CiAgICAiIiJUcnVlIGlmIHRoaXMgbWFuaWZlc3QgZGVjbGFyZXMgcGtnX25hbWUgaW4gYW55IHRhcmdldC4iIiIKICAgIHdpdGggb3BlbihwYXRoLCAiciIsIGVuY29kaW5nPSJ1dGYtOCIpIGFzIGhhbmRsZToKICAgICAgICBkb2N1bWVudCA9IGpzb24ubG9hZChoYW5kbGUpCiAgICBmb3IgdGFyZ2V0IGluIGRvY3VtZW50LmdldCgidGFyZ2V0cyIsIHt9KS52YWx1ZXMoKToKICAgICAgICBpZiBpc2luc3RhbmNlKHRhcmdldCwgZGljdCkgYW5kIGFueShrLnN0YXJ0c3dpdGgoZiJ7cGtnX25hbWV9LyIpIGZvciBrIGluIHRhcmdldCk6CiAgICAgICAgICAgIHJldHVybiBUcnVlCiAgICByZXR1cm4gRmFsc2UKCgpkZWYgdXBzZXJ0X3BhY2thZ2VfZW50cnkoZG9jdW1lbnQ6IGRpY3QsIG1lbWJlcjogZGljdCwgZmlsZV92ZXJzaW9uOiBzdHIpIC0+IGJvb2w6CiAgICAiIiJSZS1rZXkgb3IgYWRkIG9uZSBjbG9zdXJlIG1lbWJlciwgbGVhdmluZyBhbnkgb3RoZXIgbWV0YWRhdGEgb24gdGhlIGVudHJ5IGludGFjdC4iIiIKICAgIG5hbWUsIHZlcnNpb24gPSBtZW1iZXJbIm5hbWUiXSwgbWVtYmVyWyJ2ZXJzaW9uIl0KICAgIGtleSA9IGYie25hbWV9L3t2ZXJzaW9ufSIKICAgIGFzc2V0ID0geyJmaWxlVmVyc2lvbiI6IGZpbGVfdmVyc2lvbn0gaWYgZmlsZV92ZXJzaW9uIGVsc2Uge30KCiAgICBmb3IgdGFyZ2V0IGluIGRvY3VtZW50LmdldCgidGFyZ2V0cyIsIHt9KS52YWx1ZXMoKToKICAgICAgICBpZiBub3QgaXNpbnN0YW5jZSh0YXJnZXQsIGRpY3QpOgogICAgICAgICAgICBjb250aW51ZQogICAgICAgIGVudHJ5ID0ge30KICAgICAgICBmb3Igb2xkX2tleSBpbiBbayBmb3IgayBpbiB0YXJnZXQgaWYgay5zdGFydHN3aXRoKGYie25hbWV9LyIpXToKICAgICAgICAgICAgZXhpc3RpbmcgPSB0YXJnZXQucG9wKG9sZF9rZXkpCiAgICAgICAgICAgIGlmIGlzaW5zdGFuY2UoZXhpc3RpbmcsIGRpY3QpOgogICAgICAgICAgICAgICAgZW50cnkgPSBleGlzdGluZwogICAgICAgIGVudHJ5WyJydW50aW1lIl0gPSB7bWVtYmVyWyJhc3NldCJdOiBhc3NldH0KICAgICAgICB0YXJnZXRba2V5XSA9IGVudHJ5CiAgICAgICAgZm9yIHBrZ19lbnRyeSBpbiB0YXJnZXQudmFsdWVzKCk6CiAgICAgICAgICAgIGlmIGlzaW5zdGFuY2UocGtnX2VudHJ5LCBkaWN0KSBhbmQgbmFtZSBpbiBwa2dfZW50cnkuZ2V0KCJkZXBlbmRlbmNpZXMiLCB7fSk6CiAgICAgICAgICAgICAgICBwa2dfZW50cnlbImRlcGVuZGVuY2llcyJdW25hbWVdID0gdmVyc2lvbgoKICAgIGxpYnJhcmllcyA9IGRvY3VtZW50LmdldCgibGlicmFyaWVzIikKICAgIGlmIGlzaW5zdGFuY2UobGlicmFyaWVzLCBkaWN0KToKICAgICAgICBsaWJyYXJ5ID0ge30KICAgICAgICBmb3Igb2xkX2tleSBpbiBbayBmb3IgayBpbiBsaWJyYXJpZXMgaWYgay5zdGFydHN3aXRoKGYie25hbWV9LyIpXToKICAgICAgICAgICAgZXhpc3RpbmcgPSBsaWJyYXJpZXMucG9wKG9sZF9rZXkpCiAgICAgICAgICAgIGlmIGlzaW5zdGFuY2UoZXhpc3RpbmcsIGRpY3QpOgogICAgICAgICAgICAgICAgbGlicmFyeSA9IGV4aXN0aW5nCiAgICAgICAgbGlicmFyeS51cGRhdGUoewogICAgICAgICAgICAidHlwZSI6ICJwYWNrYWdlIiwgInNlcnZpY2VhYmxlIjogVHJ1ZSwgInNoYTUxMiI6ICIiLAogICAgICAgICAgICAicGF0aCI6IGYie25hbWUubG93ZXIoKX0ve3ZlcnNpb259IiwKICAgICAgICAgICAgImhhc2hQYXRoIjogZiJ7bmFtZS5sb3dlcigpfS57dmVyc2lvbn0ubnVwa2cuc2hhNTEyIiwKICAgICAgICB9KQogICAgICAgIGxpYnJhcmllc1trZXldID0gbGlicmFyeQogICAgcmV0dXJuIFRydWUKCgpkZWYgaW5zdGFsbF9jbG9zdXJlKGFwcF9yb290OiBzdHIsIGRlcHNfZmlsZXM6IGxpc3QsIHBrZ19uYW1lOiBzdHIsIHNwZWM6IGRpY3QpIC0+IE5vbmU6CiAgICAiIiJJbnN0YWxsIHRoZSBkZXBlbmRlbmN5IHNldCB0aGUgdXBncmFkZWQgcGFja2FnZSBuZWVkcyBidXQgdXBzdHJlYW0gZG9lcyBub3Qgc2hpcC4iIiIKICAgIGNsb3N1cmUgPSBzcGVjLmdldCgiY2xvc3VyZSIpIG9yIFtdCiAgICBpZiBub3QgY2xvc3VyZToKICAgICAgICByZXR1cm4KCiAgICBob3N0X2RpcnMgPSBob3N0X2RpcmVjdG9yaWVzKGFwcF9yb290LCBzcGVjWyJkbGxfbmFtZSJdKQogICAgbWFuaWZlc3RzID0gW3AgZm9yIHAgaW4gZGVwc19maWxlcyBpZiByZWZlcmVuY2VzX3BhY2thZ2UocCwgcGtnX25hbWUpXQoKICAgIGZvciBtZW1iZXIgaW4gY2xvc3VyZToKICAgICAgICBkbGxfYnl0ZXMgPSBmZXRjaF9udXBrZ19kbGwobnVnZXRfdXJsKG1lbWJlclsibmFtZSJdLCBtZW1iZXJbInZlcnNpb24iXSksIG1lbWJlclsiYXNzZXQiXSkKICAgICAgICBmaWxlX3ZlcnNpb24gPSByZWFkX2ZpbGVfdmVyc2lvbihkbGxfYnl0ZXMpCiAgICAgICAgZm9yIGRpcmVjdG9yeSBpbiBob3N0X2RpcnM6CiAgICAgICAgICAgIHdpdGggb3Blbihvcy5wYXRoLmpvaW4oZGlyZWN0b3J5LCBmInttZW1iZXJbJ25hbWUnXX0uZGxsIiksICJ3YiIpIGFzIGhhbmRsZToKICAgICAgICAgICAgICAgIGhhbmRsZS53cml0ZShkbGxfYnl0ZXMpCiAgICAgICAgZm9yIHBhdGggaW4gbWFuaWZlc3RzOgogICAgICAgICAgICB3aXRoIG9wZW4ocGF0aCwgInIiLCBlbmNvZGluZz0idXRmLTgiKSBhcyBoYW5kbGU6CiAgICAgICAgICAgICAgICBkb2N1bWVudCA9IGpzb24ubG9hZChoYW5kbGUpCiAgICAgICAgICAgIHVwc2VydF9wYWNrYWdlX2VudHJ5KGRvY3VtZW50LCBtZW1iZXIsIGZpbGVfdmVyc2lvbikKICAgICAgICAgICAgd2l0aCBvcGVuKHBhdGgsICJ3IiwgZW5jb2Rpbmc9InV0Zi04IikgYXMgaGFuZGxlOgogICAgICAgICAgICAgICAganNvbi5kdW1wKGRvY3VtZW50LCBoYW5kbGUsIGluZGVudD0yKQogICAgICAgIHByaW50KGYiLS0+IENsb3N1cmU6IHttZW1iZXJbJ25hbWUnXX0ge21lbWJlclsndmVyc2lvbiddfSAtPiB7bGVuKGhvc3RfZGlycyl9IGFwcCBkaXIocykiKQoKCmRlZiBzY2FuX3BhY2thZ2UoZGVwc19maWxlczogbGlzdCwgcGtnX25hbWU6IHN0ciwgZml4ZWRfdmVyc2lvbnM6IGxpc3QpIC0+IHR1cGxlOgogICAgIiIiUmV0dXJuIChmb3VuZF9hbnksIHJlcXVpcmVkX2ZpeCwgZGlzY292ZXJlZF92ZXJzaW9ucykgZm9yIHBrZ19uYW1lLiIiIgogICAgZm91bmRfYW55ID0gRmFsc2UKICAgIHJlcXVpcmVkX2ZpeCA9IE5vbmUKICAgIGRpc2NvdmVyZWRfdmVyc2lvbnMgPSBzZXQoKQoKICAgIGZvciBwYXRoIGluIGRlcHNfZmlsZXM6CiAgICAgICAgd2l0aCBvcGVuKHBhdGgsICJyIiwgZW5jb2Rpbmc9InV0Zi04IikgYXMgaGFuZGxlOgogICAgICAgICAgICBkb2N1bWVudCA9IGpzb24ubG9hZChoYW5kbGUpCiAgICAgICAgZm9yIHRhcmdldCBpbiBkb2N1bWVudC5nZXQoInRhcmdldHMiLCB7fSkudmFsdWVzKCk6CiAgICAgICAgICAgIGlmIG5vdCBpc2luc3RhbmNlKHRhcmdldCwgZGljdCk6CiAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICBmb3Iga2V5IGluIHRhcmdldDoKICAgICAgICAgICAgICAgIGlmIGtleS5zdGFydHN3aXRoKGYie3BrZ19uYW1lfS8iKToKICAgICAgICAgICAgICAgICAgICBmb3VuZF9hbnkgPSBUcnVlCiAgICAgICAgICAgICAgICAgICAgdl9zdHIgPSBrZXkuc3BsaXQoIi8iLCAxKVsxXQogICAgICAgICAgICAgICAgICAgIGRpc2NvdmVyZWRfdmVyc2lvbnMuYWRkKHZfc3RyKQogICAgICAgICAgICAgICAgICAgIGZpeCA9IGFwcGxpY2FibGVfZml4KHBhcnNlX3ZlcnNpb24odl9zdHIpLCBmaXhlZF92ZXJzaW9ucykKICAgICAgICAgICAgICAgICAgICBpZiBmaXggYW5kIChyZXF1aXJlZF9maXggaXMgTm9uZSBvciBmaXggPiByZXF1aXJlZF9maXgpOgogICAgICAgICAgICAgICAgICAgICAgICByZXF1aXJlZF9maXggPSBmaXgKCiAgICByZXR1cm4gZm91bmRfYW55LCByZXF1aXJlZF9maXgsIGRpc2NvdmVyZWRfdmVyc2lvbnMKCgpkZWYgcmVwbGFjZV9hc3NlbWJseShhcHBfcm9vdDogc3RyLCBkbGxfbmFtZTogc3RyLCBkbGxfYnl0ZXM6IGJ5dGVzKSAtPiBpbnQ6CiAgICAiIiJPdmVyd3JpdGUgZXZlcnkgY29weSBvZiBkbGxfbmFtZSBiZW5lYXRoIGFwcF9yb290OyByZXR1cm4gaG93IG1hbnkgd2VyZSB3cml0dGVuLiIiIgogICAgcmVwbGFjZWRfY291bnQgPSAwCiAgICBmb3Igcm9vdCwgXywgZmlsZXMgaW4gb3Mud2FsayhhcHBfcm9vdCk6CiAgICAgICAgaWYgZGxsX25hbWUgaW4gZmlsZXM6CiAgICAgICAgICAgIGRsbF9wYXRoID0gb3MucGF0aC5qb2luKHJvb3QsIGRsbF9uYW1lKQogICAgICAgICAgICB3aXRoIG9wZW4oZGxsX3BhdGgsICJ3YiIpIGFzIGhhbmRsZToKICAgICAgICAgICAgICAgIGhhbmRsZS53cml0ZShkbGxfYnl0ZXMpCiAgICAgICAgICAgIHJlcGxhY2VkX2NvdW50ICs9IDEKICAgIHJldHVybiByZXBsYWNlZF9jb3VudAoKCmRlZiByZWZyZXNoX2VudHJ5X2Fzc2V0cyhlbnRyeTogZGljdCwgcGtnX25hbWU6IHN0ciwgc3BlYzogZGljdCkgLT4gZGljdDoKICAgICIiIlJlZnJlc2ggdmVyc2lvbiBtZXRhZGF0YSBpbiBwbGFjZSwgcHJlc2VydmluZyB1cHN0cmVhbSdzIG93biBhc3NldCBsYXlvdXQuCgogICAgVGhlIGluc3RhbGwgdGFyZ2V0IHNoaXBzIHRoZSBzYW1lIGFzc2V0IHBhdGhzIHVwc3RyZWFtIGFscmVhZHkgcmVmZXJlbmNlcywgc28gdGhlCiAgICBlbnRyeSdzIHJ1bnRpbWUvcnVudGltZVRhcmdldHMga2V5cyBzdGF5IGV4YWN0bHkgYXMgcHVibGlzaGVkOyBvbmx5IHRoZSB2ZXJzaW9ucwogICAgdGhleSBhZHZlcnRpc2UgY2hhbmdlLiBSZXdyaXRpbmcgdGhlIHBhdGhzIHdvdWxkIGJlIGd1ZXNzd29yayBhYm91dCB0aGUgbGF5b3V0LgogICAgIiIiCiAgICBpZiBwa2dfbmFtZSA9PSAiTWljcm9zb2Z0LkRhdGEuU3FsQ2xpZW50IjoKICAgICAgICBkZXBlbmRlbmNpZXMgPSBlbnRyeS5nZXQoImRlcGVuZGVuY2llcyIsIHt9KQogICAgICAgIGlmICJBenVyZS5JZGVudGl0eSIgaW4gZGVwZW5kZW5jaWVzOgogICAgICAgICAgICBkZXBlbmRlbmNpZXNbIkF6dXJlLklkZW50aXR5Il0gPSBUQVJHRVRfUEFDS0FHRVNbIkF6dXJlLklkZW50aXR5Il1bInRhcmdldF92ZXJzaW9uX3N0ciJdCgogICAgZmlsZV92ZXJzaW9uID0gc3BlYy5nZXQoIm9ic2VydmVkX2ZpbGVfdmVyc2lvbiIpCiAgICBhc3NlbWJseV92ZXJzaW9uID0gc3BlYy5nZXQoImFzc2VtYmx5X3ZlcnNpb24iKQoKICAgIGZvciBzZWN0aW9uIGluICgicnVudGltZSIsICJydW50aW1lVGFyZ2V0cyIpOgogICAgICAgIGFzc2V0cyA9IGVudHJ5LmdldChzZWN0aW9uKQogICAgICAgIGlmIG5vdCBpc2luc3RhbmNlKGFzc2V0cywgZGljdCk6CiAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgZm9yIG1ldGEgaW4gYXNzZXRzLnZhbHVlcygpOgogICAgICAgICAgICBpZiBub3QgaXNpbnN0YW5jZShtZXRhLCBkaWN0KToKICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgIGlmIGZpbGVfdmVyc2lvbjoKICAgICAgICAgICAgICAgIG1ldGFbImZpbGVWZXJzaW9uIl0gPSBmaWxlX3ZlcnNpb24KICAgICAgICAgICAgaWYgYXNzZW1ibHlfdmVyc2lvbjoKICAgICAgICAgICAgICAgIG1ldGFbImFzc2VtYmx5VmVyc2lvbiJdID0gYXNzZW1ibHlfdmVyc2lvbgoKICAgIHJldHVybiBlbnRyeQoKCmRlZiBwYXRjaF90YXJnZXRzKGRvY3VtZW50OiBkaWN0LCBwa2dfbmFtZTogc3RyLCBzcGVjOiBkaWN0KSAtPiBib29sOgogICAgIiIiUmUta2V5IGFuZCByZXdyaXRlIGV2ZXJ5IHRhcmdldCBlbnRyeSBhbmQgZGVwZW5kZW5jeSByYW5nZSBmb3IgcGtnX25hbWUuIiIiCiAgICBtb2RpZmllZCA9IEZhbHNlCiAgICBuZXdfa2V5ID0gZiJ7cGtnX25hbWV9L3tzcGVjWyd0YXJnZXRfdmVyc2lvbl9zdHInXX0iCgogICAgZm9yIHRhcmdldCBpbiBkb2N1bWVudC5nZXQoInRhcmdldHMiLCB7fSkudmFsdWVzKCk6CiAgICAgICAgaWYgbm90IGlzaW5zdGFuY2UodGFyZ2V0LCBkaWN0KToKICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgZm9yIG9sZF9rZXkgaW4gW2sgZm9yIGsgaW4gdGFyZ2V0IGlmIGsuc3RhcnRzd2l0aChmIntwa2dfbmFtZX0vIildOgogICAgICAgICAgICBlbnRyeSA9IHRhcmdldC5wb3Aob2xkX2tleSkKICAgICAgICAgICAgaWYgaXNpbnN0YW5jZShlbnRyeSwgZGljdCk6CiAgICAgICAgICAgICAgICBlbnRyeSA9IHJlZnJlc2hfZW50cnlfYXNzZXRzKGVudHJ5LCBwa2dfbmFtZSwgc3BlYykKICAgICAgICAgICAgdGFyZ2V0W25ld19rZXldID0gZW50cnkKICAgICAgICAgICAgbW9kaWZpZWQgPSBUcnVlCgogICAgICAgIGZvciBwa2dfZW50cnkgaW4gdGFyZ2V0LnZhbHVlcygpOgogICAgICAgICAgICBpZiBpc2luc3RhbmNlKHBrZ19lbnRyeSwgZGljdCkgYW5kIHBrZ19uYW1lIGluIHBrZ19lbnRyeS5nZXQoImRlcGVuZGVuY2llcyIsIHt9KToKICAgICAgICAgICAgICAgIHBrZ19lbnRyeVsiZGVwZW5kZW5jaWVzIl1bcGtnX25hbWVdID0gc3BlY1sidGFyZ2V0X3ZlcnNpb25fc3RyIl0KICAgICAgICAgICAgICAgIG1vZGlmaWVkID0gVHJ1ZQoKICAgIHJldHVybiBtb2RpZmllZAoKCmRlZiBwYXRjaF9saWJyYXJpZXMoZG9jdW1lbnQ6IGRpY3QsIHBrZ19uYW1lOiBzdHIsIHNwZWM6IGRpY3QpIC0+IGJvb2w6CiAgICAiIiJSZS1rZXkgdGhlIGxpYnJhcmllcyBzZWN0aW9uIGFuZCBkcm9wIHRoZSBub3ctc3RhbGUgcGFja2FnZSBoYXNoLiIiIgogICAgbW9kaWZpZWQgPSBGYWxzZQogICAgbGlicmFyaWVzID0gZG9jdW1lbnQuZ2V0KCJsaWJyYXJpZXMiLCB7fSkKICAgIHZlcnNpb24gPSBzcGVjWyJ0YXJnZXRfdmVyc2lvbl9zdHIiXQoKICAgIGZvciBvbGRfa2V5IGluIFtrIGZvciBrIGluIGxpYnJhcmllcyBpZiBrLnN0YXJ0c3dpdGgoZiJ7cGtnX25hbWV9LyIpXToKICAgICAgICBsaWJyYXJ5ID0gbGlicmFyaWVzLnBvcChvbGRfa2V5KQogICAgICAgIGlmIGlzaW5zdGFuY2UobGlicmFyeSwgZGljdCk6CiAgICAgICAgICAgIGxpYnJhcnlbInBhdGgiXSA9IGYie3BrZ19uYW1lLmxvd2VyKCl9L3t2ZXJzaW9ufSIKICAgICAgICAgICAgbGlicmFyeVsiaGFzaFBhdGgiXSA9IGYie3BrZ19uYW1lLmxvd2VyKCl9Lnt2ZXJzaW9ufS5udXBrZy5zaGE1MTIiCiAgICAgICAgICAgICMgVGhlIHJlY29yZGVkIGhhc2ggYmVsb25ncyB0byB0aGUgc3VwZXJzZWRlZCBwYWNrYWdlOyBrZWVwaW5nIGl0IHdvdWxkCiAgICAgICAgICAgICMgYXNzZXJ0IGFuIGludGVncml0eSB2YWx1ZSB0aGF0IG5vIGxvbmdlciBtYXRjaGVzIHRoZSBzaGlwcGVkIGFzc2VtYmx5LgogICAgICAgICAgICBpZiAic2hhNTEyIiBpbiBsaWJyYXJ5OgogICAgICAgICAgICAgICAgbGlicmFyeVsic2hhNTEyIl0gPSAiIgogICAgICAgIGxpYnJhcmllc1tmIntwa2dfbmFtZX0ve3ZlcnNpb259Il0gPSBsaWJyYXJ5CiAgICAgICAgbW9kaWZpZWQgPSBUcnVlCgogICAgcmV0dXJuIG1vZGlmaWVkCgoKZGVmIHBhdGNoX2RlcHNfZmlsZShwYXRoOiBzdHIsIHBrZ19uYW1lOiBzdHIsIHNwZWM6IGRpY3QpIC0+IGJvb2w6CiAgICAiIiJBcHBseSB0YXJnZXQgYW5kIGxpYnJhcnkgcmV3cml0ZXMgdG8gYSBzaW5nbGUgLmRlcHMuanNvbjsgcmV0dXJuIFRydWUgaWYgd3JpdHRlbi4iIiIKICAgIHdpdGggb3BlbihwYXRoLCAiciIsIGVuY29kaW5nPSJ1dGYtOCIpIGFzIGhhbmRsZToKICAgICAgICBkb2N1bWVudCA9IGpzb24ubG9hZChoYW5kbGUpCgogICAgbW9kaWZpZWQgPSBwYXRjaF90YXJnZXRzKGRvY3VtZW50LCBwa2dfbmFtZSwgc3BlYykKICAgIG1vZGlmaWVkID0gcGF0Y2hfbGlicmFyaWVzKGRvY3VtZW50LCBwa2dfbmFtZSwgc3BlYykgb3IgbW9kaWZpZWQKCiAgICBpZiBtb2RpZmllZDoKICAgICAgICB3aXRoIG9wZW4ocGF0aCwgInciLCBlbmNvZGluZz0idXRmLTgiKSBhcyBoYW5kbGU6CiAgICAgICAgICAgIGpzb24uZHVtcChkb2N1bWVudCwgaGFuZGxlLCBpbmRlbnQ9MikKICAgIHJldHVybiBtb2RpZmllZAoKCmRlZiB1cGdyYWRlX3BhY2thZ2UoYXBwX3Jvb3Q6IHN0ciwgZGVwc19maWxlczogbGlzdCwgcGtnX25hbWU6IHN0ciwgZGlzY292ZXJlZDogc2V0KSAtPiBOb25lOgogICAgIiIiRmV0Y2gsIGluc3RhbGwgYW5kIHJlY29yZCB0aGUgc2FmZSB2ZXJzaW9uIG9mIG9uZSB2dWxuZXJhYmxlIHBhY2thZ2UuIiIiCiAgICBzcGVjID0gVEFSR0VUX1BBQ0tBR0VTW3BrZ19uYW1lXQogICAgdGFyZ2V0ID0gcGFyc2VfdmVyc2lvbihzcGVjWyJ0YXJnZXRfdmVyc2lvbl9zdHIiXSkKICAgIG5ld2VzdCA9IG1heCgocGFyc2VfdmVyc2lvbih2KSBmb3IgdiBpbiBkaXNjb3ZlcmVkKSwgZGVmYXVsdD10YXJnZXQpCiAgICBpZiBuZXdlc3QgPiB0YXJnZXQ6CiAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKAogICAgICAgICAgICBmIntwa2dfbmFtZX06IHVwc3RyZWFtIHNoaXBzIHttYXgoZGlzY292ZXJlZCwga2V5PXBhcnNlX3ZlcnNpb24pfSBidXQgdGhpcyBwb2xpY3kgb25seSAiCiAgICAgICAgICAgIGYicGlucyB7c3BlY1sndGFyZ2V0X3ZlcnNpb25fc3RyJ119LiBJbnN0YWxsaW5nIGl0IHdvdWxkIGJlIGEgZG93bmdyYWRlOyB0aGUgcGlubmVkICIKICAgICAgICAgICAgInRhcmdldCBuZWVkcyB1cGRhdGluZyB0byB0aGUgZml4IG9uIHVwc3RyZWFtJ3MgY3VycmVudCBicmFuY2guIgogICAgICAgICkKICAgIHByaW50KGYiLS0+IEZldGNoaW5nIHtwa2dfbmFtZX0ge3NwZWNbJ3RhcmdldF92ZXJzaW9uX3N0ciddfSBmcm9tIE51R2V0Li4uIikKCiAgICBpZiBzcGVjLmdldCgiYXNzZXRfa2luZCIpID09ICJuYXRpdmUiOgogICAgICAgIHJlcGxhY2VkX2NvdW50ID0gcmVwbGFjZV9yaWRfYXNzZXRzKGFwcF9yb290LCBmZXRjaF9udXBrZyhzcGVjWyJudXBrZ191cmwiXSksIHNwZWNbImRsbF9uYW1lIl0pCiAgICBlbHNlOgogICAgICAgIGRsbF9ieXRlcyA9IGZldGNoX251cGtnX2RsbChzcGVjWyJudXBrZ191cmwiXSwgc3BlY1siZGxsX3JlbF9wYXRoIl0pCiAgICAgICAgIyBSZWNvcmQgd2hhdCB0aGUgYXNzZW1ibHkgcmVwb3J0czsgdGhlcmUgaXMgbm8gaGFyZGNvZGVkIGxpdGVyYWwgdG8gZHJpZnQuCiAgICAgICAgc3BlY1sib2JzZXJ2ZWRfZmlsZV92ZXJzaW9uIl0gPSByZWFkX2ZpbGVfdmVyc2lvbihkbGxfYnl0ZXMpCiAgICAgICAgcmVwbGFjZWRfY291bnQgPSByZXBsYWNlX2Fzc2VtYmx5KGFwcF9yb290LCBzcGVjWyJkbGxfbmFtZSJdLCBkbGxfYnl0ZXMpCgogICAgaWYgcmVwbGFjZWRfY291bnQgPT0gMDoKICAgICAgICByYWlzZSBSdW50aW1lRXJyb3IoCiAgICAgICAgICAgIGYie3BrZ19uYW1lfTogJ3tzcGVjWydkbGxfbmFtZSddfScgaXMgZGVjbGFyZWQgaW4gYSAuZGVwcy5qc29uIGJ1dCBubyBjb3B5IGV4aXN0cyAiCiAgICAgICAgICAgIGYidW5kZXIge2FwcF9yb290fS4gUmVmdXNpbmcgdG8gcmVjb3JkIHtzcGVjWyd0YXJnZXRfdmVyc2lvbl9zdHInXX0gaW4gdGhlIG1hbmlmZXN0LCAiCiAgICAgICAgICAgICJ3aGljaCB3b3VsZCByZXBvcnQgYSBwYXRjaGVkIHZlcnNpb24gd2hpbGUgdGhlIHZ1bG5lcmFibGUgYXNzZW1ibHkgcmVtYWlucy4iCiAgICAgICAgKQogICAgcHJpbnQoZiItLT4gUmVwbGFjZWQge3JlcGxhY2VkX2NvdW50fSBpbnN0YW5jZShzKSBvZiB7c3BlY1snZGxsX25hbWUnXX0gaW4ge2FwcF9yb290fSIpCgogICAgZm9yIHBhdGggaW4gZGVwc19maWxlczoKICAgICAgICBwYXRjaF9kZXBzX2ZpbGUocGF0aCwgcGtnX25hbWUsIHNwZWMpCgogICAgaW5zdGFsbF9jbG9zdXJlKGFwcF9yb290LCBkZXBzX2ZpbGVzLCBwa2dfbmFtZSwgc3BlYykKCgpkZWYgcmVtZWRpYXRlX2FwcF9kZXBlbmRlbmNpZXMoYXBwX3Jvb3Q6IHN0ciA9ICIvYXBwIikgLT4gTm9uZToKICAgICIiIlNjYW4gYW5kIGNvbmRpdGlvbmFsbHkgcmVtZWRpYXRlIHZ1bG5lcmFibGUgTnVHZXQgcGFja2FnZXMgaW4gYXBwX3Jvb3QuIiIiCiAgICBkZXBzX2ZpbGVzID0gZmluZF9kZXBzX2ZpbGVzKGFwcF9yb290KQogICAgcGFja2FnZXNfdG9fdXBncmFkZSA9IFtdCgogICAgZm9yIHBrZ19uYW1lLCBzcGVjIGluIFRBUkdFVF9QQUNLQUdFUy5pdGVtcygpOgogICAgICAgIGZvdW5kX2FueSwgcmVxdWlyZWRfZml4LCB2ZXJzaW9ucyA9IHNjYW5fcGFja2FnZSgKICAgICAgICAgICAgZGVwc19maWxlcywgcGtnX25hbWUsIHNwZWNbImFkdmlzb3J5X2ZpeGVkX3ZlcnNpb25zIl0KICAgICAgICApCiAgICAgICAgdl9saXN0ID0gIiwgIi5qb2luKHNvcnRlZCh2ZXJzaW9ucykpCgogICAgICAgIGlmIG5vdCBmb3VuZF9hbnk6CiAgICAgICAgICAgIHByaW50KGYiW1VQU1RSRUFNIENMRUFOXSB7cGtnX25hbWV9OiBOb3QgcHJlc2VudCBpbiB1cHN0cmVhbSBkZXBlbmRlbmNpZXMuIFNraXBwZWQuIikKICAgICAgICBlbGlmIHJlcXVpcmVkX2ZpeCBpcyBOb25lOgogICAgICAgICAgICBwcmludCgKICAgICAgICAgICAgICAgIGYiW1VQU1RSRUFNIENMRUFOXSB7cGtnX25hbWV9OiBVcHN0cmVhbSB2ZXJzaW9uKHMpICh7dl9saXN0fSkgYXJlIGF0IG9yIHBhc3QgdGhlIGZpeCBwdWJsaXNoZWQgZm9yIHRoZWlyIGJyYW5jaC4gTm8gcGF0Y2ggbmVlZGVkLiIKICAgICAgICAgICAgKQogICAgICAgIGVsc2U6CiAgICAgICAgICAgIGZpeF9zdHIgPSAiLiIuam9pbihzdHIobikgZm9yIG4gaW4gcmVxdWlyZWRfZml4KQogICAgICAgICAgICBwcmludCgKICAgICAgICAgICAgICAgIGYiW1JFTUVESUFURV0ge3BrZ19uYW1lfTogVXBzdHJlYW0gdmVyc2lvbihzKSAoe3ZfbGlzdH0pIHByZWRhdGUgdGhlIGJyYW5jaCBmaXgge2ZpeF9zdHJ9LiBVcGdyYWRpbmcgdG8ge3NwZWNbJ3RhcmdldF92ZXJzaW9uX3N0ciddfS4uLiIKICAgICAgICAgICAgKQogICAgICAgICAgICBwYWNrYWdlc190b191cGdyYWRlLmFwcGVuZCgocGtnX25hbWUsIHZlcnNpb25zKSkKCiAgICBmb3IgcGtnX25hbWUsIHZlcnNpb25zIGluIHBhY2thZ2VzX3RvX3VwZ3JhZGU6CiAgICAgICAgdXBncmFkZV9wYWNrYWdlKGFwcF9yb290LCBkZXBzX2ZpbGVzLCBwa2dfbmFtZSwgdmVyc2lvbnMpCgogICAgcHJpbnQoIlN0YWdlIDE6IER5bmFtaWMgcmVtZWRpYXRpb24gY2hlY2sgY29tcGxldGUuIikKCgppZiBfX25hbWVfXyA9PSAiX19tYWluX18iOgogICAgcmVtZWRpYXRlX2FwcF9kZXBlbmRlbmNpZXMoIi9hcHAiKQo=" | base64 -d | python3


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
    # Strip setuid/setgid bits across system binaries to prevent privilege escalation.
    # sudo and su are exempt: the upstream entrypoint adds the runtime user to sudoers
    # and launches the server via `su`, so clearing their setuid bit breaks the app.
    find /bin /sbin /usr/bin /usr/sbin -perm /6000 -type f \
        ! -name 'sudo' ! -name 'sudo.ws' ! -name 'su' \
        -exec chmod a-s {} + 2>/dev/null || true && \
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
# Stage 2c: Flavor CUDA (Host-Based NVIDIA CUDA / NVENC / NVDEC)
# ==============================================================================
FROM base-common AS base-cuda

# Host-based NVIDIA acceleration:
# Relies directly on host-injected driver libraries (libcuda.so.1, libnvidia-encode.so.1,
# libnvcuvid.so.1) via NVIDIA Container Toolkit with zero in-container package bloat.

# ==============================================================================
# Stage 2d: Flavor CUDA 13 (Minimal Cutting-Edge NVIDIA CUDA 13.4+ Runtime & Filters)
# ==============================================================================
FROM base-common AS base-cuda13

ARG DEBIAN_FRONTEND=noninteractive

RUN if [ "$(dpkg --print-architecture)" = "amd64" ]; then \
        curl -fsSL https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2604/x86_64/cuda-keyring_1.1-1_all.deb -o /tmp/cuda-keyring.deb && \
        dpkg -i /tmp/cuda-keyring.deb && \
        rm -f /tmp/cuda-keyring.deb && \
        apt-get update && \
        apt-get install -y --no-install-recommends \
            cuda-cudart-13-4 \
            cuda-nvrtc-13-4 \
            libnpp-13-4 && \
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
ENV PATH=/usr/local/cuda-13.4/bin:/usr/local/cuda-13.3/bin:/usr/local/cuda-12.8/bin:/usr/local/cuda/bin:/dotnet:/dotnet/tools:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LD_LIBRARY_PATH=/usr/local/cuda-13.4/lib64:/usr/local/cuda-13.3/lib64:/usr/local/cuda-12.8/lib64:/usr/local/cuda/lib64 \
    DOTNET_ROOT=/dotnet \
    NVIDIA_DRIVER_CAPABILITIES=compute,video,utility \
    NVIDIA_VISIBLE_DEVICES=all \
    DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_NOLOGO=1 \
    DOTNET_EnableDiagnostics=0 \
    DOTNET_gcServer=1 \
    DOTNET_TieredPGO=1 \
    DOTNET_TC_QuickJitForLoops=1

# Copy custom utility binaries tolerantly from upstream staging if present
COPY --from=upstream /extra-bin/ /usr/local/bin/

# Copy pruned application directory directly from upstream stage
COPY --from=upstream /app /app

# Align the PAM/su environment with the image PATH, ensure execution permissions,
# idempotently neutralize runtime apt-get calls, and inject invariant Real Image marker.
# The entrypoint drops privileges with `su`, which resets PATH from /etc/environment and
# /etc/login.defs -- discarding /dotnet and the CUDA bin directories and reintroducing
# /snap/bin after snapd was pinned out of the image.
RUN printf 'PATH="%s"\n' "$PATH" > /etc/environment && \
    sed -i -E "s|^ENV_SUPATH[[:space:]]+PATH=.*|ENV_SUPATH\tPATH=$PATH|; \
               s|^ENV_PATH[[:space:]]+PATH=.*|ENV_PATH\tPATH=$PATH|" /etc/login.defs && \
    chmod +x /app/docker-entrypoint.sh && \
    chmod +x /usr/local/bin/* 2>/dev/null || true && \
    sed -i -E 's/apt-get update.*intel-media-va-driver.*/echo "[FileFlows Real Image] Hardware acceleration pre-configured."/g' /app/docker-entrypoint.sh || true && \
    sed -i '/Installing intel-media-va-driver-non-free/d' /app/docker-entrypoint.sh || true && \
    sed -i "2i echo \"[FileFlows Real Image] Initializing optimized runtime (${FLAVOR})...\"" /app/docker-entrypoint.sh

# Expose web UI port
EXPOSE 5000/tcp

# Healthcheck validating FileFlows web interface
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f -s http://127.0.0.1:5000/initial-config || curl -f -s http://127.0.0.1:5000/ || exit 1

WORKDIR /app

ENTRYPOINT ["/app/docker-entrypoint.sh"]
