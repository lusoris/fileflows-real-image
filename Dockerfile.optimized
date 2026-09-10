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
# - Resolves CVE-2023-36414, CVE-2024-29992, CVE-2024-35255 (Azure.Identity < 1.21.0)
# - Resolves CVE-2024-0056 (Microsoft.Data.SqlClient < 5.2.2)
# - Resolves CVE-2021-24112 (System.Drawing.Common < 8.0.0)
RUN echo "IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwoiIiIKRHluYW1pYyBTZW1hbnRpYyBOdUdldCBWdWxuZXJhYmlsaXR5IFJlbWVkaWF0b3IgZm9yIEZpbGVGbG93cyBSZWFsIEltYWdlLgoKLSBJbnNwZWN0cyBhY3RpdmUgdmVyc2lvbnMgYWNyb3NzIGFsbCAvYXBwLyoqLyouZGVwcy5qc29uIGZpbGVzLgotIElmIHVwc3RyZWFtIGhhcyBhbHJlYWR5IHVwZ3JhZGVkIHRvIG9yIGJleW9uZCBzYWZlIG1pbmltdW0gdmVyc2lvbnMsIHByZXNlcnZlcyB1cHN0cmVhbSAobm8gZG93bmdyYWRlKS4KLSBJZiBwYWNrYWdlcyBhcmUgdnVsbmVyYWJsZSBvciBvbGRlciB0aGFuIHNhZmUgbWluaW11bXMsIHVwZ3JhZGVzIGFzc2VtYmx5IGFuZCBwYXRjaGVzIC5kZXBzLmpzb24uCi0gUmVzb2x2ZXMgQ1ZFLTIwMjMtMzY0MTQsIENWRS0yMDI0LTI5OTkyLCBDVkUtMjAyNC0zNTI1NSAoQXp1cmUuSWRlbnRpdHkgPCAxLjIxLjApCi0gUmVzb2x2ZXMgQ1ZFLTIwMjQtMDA1NiAoTWljcm9zb2Z0LkRhdGEuU3FsQ2xpZW50IDwgNS4yLjIpCi0gUmVzb2x2ZXMgQ1ZFLTIwMjEtMjQxMTIgKFN5c3RlbS5EcmF3aW5nLkNvbW1vbiA8IDguMC4wKQoiIiIKCmltcG9ydCBnbG9iCmltcG9ydCBpbwppbXBvcnQganNvbgppbXBvcnQgb3MKaW1wb3J0IHJlCmltcG9ydCB1cmxsaWIucmVxdWVzdAppbXBvcnQgemlwZmlsZQoKVEFSR0VUX1BBQ0tBR0VTID0gewogICAgIkF6dXJlLklkZW50aXR5IjogewogICAgICAgICJtaW5fdmVyc2lvbiI6ICgxLCAyMSwgMCksCiAgICAgICAgInRhcmdldF92ZXJzaW9uX3N0ciI6ICIxLjIxLjAiLAogICAgICAgICJudXBrZ191cmwiOiAiaHR0cHM6Ly9hcGkubnVnZXQub3JnL3YzLWZsYXRjb250YWluZXIvYXp1cmUuaWRlbnRpdHkvMS4yMS4wL2F6dXJlLmlkZW50aXR5LjEuMjEuMC5udXBrZyIsCiAgICAgICAgImRsbF9yZWxfcGF0aCI6ICJsaWIvbmV0MTAuMC9BenVyZS5JZGVudGl0eS5kbGwiLAogICAgICAgICJkbGxfbmFtZSI6ICJBenVyZS5JZGVudGl0eS5kbGwiLAogICAgICAgICJhc3NlbWJseV92ZXJzaW9uIjogIjEuMjEuMC4wIiwKICAgICAgICAiZmlsZV92ZXJzaW9uIjogIjEuMjEwMC4yNi4xMTUwMSIsCiAgICB9LAogICAgIk1pY3Jvc29mdC5EYXRhLlNxbENsaWVudCI6IHsKICAgICAgICAibWluX3ZlcnNpb24iOiAoNSwgMiwgMiksCiAgICAgICAgInRhcmdldF92ZXJzaW9uX3N0ciI6ICI1LjIuMiIsCiAgICAgICAgIm51cGtnX3VybCI6ICJodHRwczovL2FwaS5udWdldC5vcmcvdjMtZmxhdGNvbnRhaW5lci9taWNyb3NvZnQuZGF0YS5zcWxjbGllbnQvNS4yLjIvbWljcm9zb2Z0LmRhdGEuc3FsY2xpZW50LjUuMi4yLm51cGtnIiwKICAgICAgICAiZGxsX3JlbF9wYXRoIjogInJ1bnRpbWVzL3VuaXgvbGliL25ldDguMC9NaWNyb3NvZnQuRGF0YS5TcWxDbGllbnQuZGxsIiwKICAgICAgICAiZGxsX25hbWUiOiAiTWljcm9zb2Z0LkRhdGEuU3FsQ2xpZW50LmRsbCIsCiAgICAgICAgImFzc2VtYmx5X3ZlcnNpb24iOiAiNS4wLjAuMCIsCiAgICAgICAgImZpbGVfdmVyc2lvbiI6ICI1LjIwMi4yNDI2My4yIiwKICAgIH0sCiAgICAiU3lzdGVtLkRyYXdpbmcuQ29tbW9uIjogewogICAgICAgICJtaW5fdmVyc2lvbiI6ICg4LCAwLCAwKSwKICAgICAgICAidGFyZ2V0X3ZlcnNpb25fc3RyIjogIjguMC4wIiwKICAgICAgICAibnVwa2dfdXJsIjogImh0dHBzOi8vYXBpLm51Z2V0Lm9yZy92My1mbGF0Y29udGFpbmVyL3N5c3RlbS5kcmF3aW5nLmNvbW1vbi84LjAuMC9zeXN0ZW0uZHJhd2luZy5jb21tb24uOC4wLjAubnVwa2ciLAogICAgICAgICJkbGxfcmVsX3BhdGgiOiAibGliL25ldHN0YW5kYXJkMi4wL1N5c3RlbS5EcmF3aW5nLkNvbW1vbi5kbGwiLAogICAgICAgICJkbGxfbmFtZSI6ICJTeXN0ZW0uRHJhd2luZy5Db21tb24uZGxsIiwKICAgICAgICAiYXNzZW1ibHlfdmVyc2lvbiI6ICI4LjAuMC4wIiwKICAgICAgICAiZmlsZV92ZXJzaW9uIjogIjguMC4yMy41MzEwNSIsCiAgICB9LAp9CgoKZGVmIHBhcnNlX3ZlcnNpb24odl9zdHI6IHN0cikgLT4gdHVwbGU6CiAgICAiIiJQYXJzZSBzZW1hbnRpYyB2ZXJzaW9uIHN0cmluZyBpbnRvIGEgY29tcGFyYWJsZSB0dXBsZSBvZiBpbnRlZ2Vycy4iIiIKICAgIHBhcnRzID0gcmUuZmluZGFsbChyIlxkKyIsIHZfc3RyLnNwbGl0KCItIilbMF0pCiAgICByZXR1cm4gdHVwbGUobWFwKGludCwgcGFydHMpKSBpZiBwYXJ0cyBlbHNlICgwLCkKCgpkZWYgZmV0Y2hfbnVwa2codXJsOiBzdHIpIC0+IHppcGZpbGUuWmlwRmlsZToKICAgICIiIkRvd25sb2FkIGFuZCBvcGVuIGEgTnVHZXQgcGFja2FnZSB6aXAgZmlsZSBmcm9tIGEgVVJMLiIiIgogICAgcmVxID0gdXJsbGliLnJlcXVlc3QuUmVxdWVzdCh1cmwsIGhlYWRlcnM9eyJVc2VyLUFnZW50IjogIkZpbGVGbG93cy1SZWFsLUltYWdlLzEuMCJ9KQogICAgd2l0aCB1cmxsaWIucmVxdWVzdC51cmxvcGVuKHJlcSkgYXMgcmVzcDoKICAgICAgICByZXR1cm4gemlwZmlsZS5aaXBGaWxlKGlvLkJ5dGVzSU8ocmVzcC5yZWFkKCkpKQoKCmRlZiByZW1lZGlhdGVfYXBwX2RlcGVuZGVuY2llcyhhcHBfcm9vdDogc3RyID0gIi9hcHAiKSAtPiBOb25lOgogICAgIiIiU2NhbiBhbmQgY29uZGl0aW9uYWxseSByZW1lZGlhdGUgdnVsbmVyYWJsZSBOdUdldCBwYWNrYWdlcyBpbiBhcHBfcm9vdC4iIiIKICAgIGRlcHNfZmlsZXMgPSBzb3J0ZWQoZ2xvYi5nbG9iKGYie2FwcF9yb290fS8qKi8qLmRlcHMuanNvbiIsIHJlY3Vyc2l2ZT1UcnVlKSkKICAgIHBhY2thZ2VzX3RvX3VwZ3JhZGUgPSBzZXQoKQoKICAgIGZvciBwa2dfbmFtZSwgc3BlYyBpbiBUQVJHRVRfUEFDS0FHRVMuaXRlbXMoKToKICAgICAgICBmb3VuZF9hbnkgPSBGYWxzZQogICAgICAgIG5lZWRzX3VwZ3JhZGUgPSBGYWxzZQogICAgICAgIGRpc2NvdmVyZWRfdmVyc2lvbnMgPSBzZXQoKQoKICAgICAgICBmb3IgcCBpbiBkZXBzX2ZpbGVzOgogICAgICAgICAgICB3aXRoIG9wZW4ocCwgInIiLCBlbmNvZGluZz0idXRmLTgiKSBhcyBmOgogICAgICAgICAgICAgICAgZCA9IGpzb24ubG9hZChmKQogICAgICAgICAgICBmb3IgdGFyZ2V0IGluIGQuZ2V0KCJ0YXJnZXRzIiwge30pLnZhbHVlcygpOgogICAgICAgICAgICAgICAgZm9yIGtleSBpbiB0YXJnZXQ6CiAgICAgICAgICAgICAgICAgICAgaWYga2V5LnN0YXJ0c3dpdGgoZiJ7cGtnX25hbWV9LyIpOgogICAgICAgICAgICAgICAgICAgICAgICBmb3VuZF9hbnkgPSBUcnVlCiAgICAgICAgICAgICAgICAgICAgICAgIHZfc3RyID0ga2V5LnNwbGl0KCIvIilbMV0KICAgICAgICAgICAgICAgICAgICAgICAgZGlzY292ZXJlZF92ZXJzaW9ucy5hZGQodl9zdHIpCiAgICAgICAgICAgICAgICAgICAgICAgIGlmIHBhcnNlX3ZlcnNpb24odl9zdHIpIDwgc3BlY1sibWluX3ZlcnNpb24iXToKICAgICAgICAgICAgICAgICAgICAgICAgICAgIG5lZWRzX3VwZ3JhZGUgPSBUcnVlCgogICAgICAgIGlmIG5vdCBmb3VuZF9hbnk6CiAgICAgICAgICAgIHByaW50KGYiW1VQU1RSRUFNIENMRUFOXSB7cGtnX25hbWV9OiBOb3QgcHJlc2VudCBpbiB1cHN0cmVhbSBkZXBlbmRlbmNpZXMuIFNraXBwZWQuIikKICAgICAgICBlbGlmIG5vdCBuZWVkc191cGdyYWRlOgogICAgICAgICAgICB2X2xpc3QgPSAiLCAiLmpvaW4oc29ydGVkKGRpc2NvdmVyZWRfdmVyc2lvbnMpKQogICAgICAgICAgICBwcmludCgKICAgICAgICAgICAgICAgIGYiW1VQU1RSRUFNIENMRUFOXSB7cGtnX25hbWV9OiBVcHN0cmVhbSB2ZXJzaW9uKHMpICh7dl9saXN0fSkgbWVldCBvciBleGNlZWQgdGFyZ2V0IHNhZmUgdmVyc2lvbiAoe3NwZWNbJ3RhcmdldF92ZXJzaW9uX3N0ciddfSkuIE5vIHBhdGNoIG5lZWRlZC4iCiAgICAgICAgICAgICkKICAgICAgICBlbHNlOgogICAgICAgICAgICB2X2xpc3QgPSAiLCAiLmpvaW4oc29ydGVkKGRpc2NvdmVyZWRfdmVyc2lvbnMpKQogICAgICAgICAgICBwcmludCgKICAgICAgICAgICAgICAgIGYiW1JFTUVESUFURV0ge3BrZ19uYW1lfTogVXBzdHJlYW0gdmVyc2lvbihzKSAoe3ZfbGlzdH0pIGJlbG93IHNhZmUgdGhyZXNob2xkICh7c3BlY1sndGFyZ2V0X3ZlcnNpb25fc3RyJ119KS4gVXBncmFkaW5nLi4uIgogICAgICAgICAgICApCiAgICAgICAgICAgIHBhY2thZ2VzX3RvX3VwZ3JhZGUuYWRkKHBrZ19uYW1lKQoKICAgIGZvciBwa2dfbmFtZSBpbiBwYWNrYWdlc190b191cGdyYWRlOgogICAgICAgIHNwZWMgPSBUQVJHRVRfUEFDS0FHRVNbcGtnX25hbWVdCiAgICAgICAgcHJpbnQoZiItLT4gRmV0Y2hpbmcge3BrZ19uYW1lfSB7c3BlY1sndGFyZ2V0X3ZlcnNpb25fc3RyJ119IGZyb20gTnVHZXQuLi4iKQogICAgICAgIHogPSBmZXRjaF9udXBrZyhzcGVjWyJudXBrZ191cmwiXSkKICAgICAgICBkbGxfYnl0ZXMgPSB6LnJlYWQoc3BlY1siZGxsX3JlbF9wYXRoIl0pCgogICAgICAgIHJlcGxhY2VkX2NvdW50ID0gMAogICAgICAgIGZvciByb290LCBfLCBmaWxlcyBpbiBvcy53YWxrKGFwcF9yb290KToKICAgICAgICAgICAgaWYgc3BlY1siZGxsX25hbWUiXSBpbiBmaWxlczoKICAgICAgICAgICAgICAgIGRsbF9wYXRoID0gb3MucGF0aC5qb2luKHJvb3QsIHNwZWNbImRsbF9uYW1lIl0pCiAgICAgICAgICAgICAgICB3aXRoIG9wZW4oZGxsX3BhdGgsICJ3YiIpIGFzIGY6CiAgICAgICAgICAgICAgICAgICAgZi53cml0ZShkbGxfYnl0ZXMpCiAgICAgICAgICAgICAgICByZXBsYWNlZF9jb3VudCArPSAxCiAgICAgICAgcHJpbnQoZiItLT4gUmVwbGFjZWQge3JlcGxhY2VkX2NvdW50fSBpbnN0YW5jZShzKSBvZiB7c3BlY1snZGxsX25hbWUnXX0gaW4ge2FwcF9yb290fSIpCgogICAgICAgIGZvciBwIGluIGRlcHNfZmlsZXM6CiAgICAgICAgICAgIHdpdGggb3BlbihwLCAiciIsIGVuY29kaW5nPSJ1dGYtOCIpIGFzIGY6CiAgICAgICAgICAgICAgICBkID0ganNvbi5sb2FkKGYpCgogICAgICAgICAgICBtb2RpZmllZCA9IEZhbHNlCiAgICAgICAgICAgIGZvciB0YXJnZXQgaW4gZC5nZXQoInRhcmdldHMiLCB7fSkudmFsdWVzKCk6CiAgICAgICAgICAgICAgICBvbGRfa2V5cyA9IFtrIGZvciBrIGluIHRhcmdldCBpZiBrLnN0YXJ0c3dpdGgoZiJ7cGtnX25hbWV9LyIpXQogICAgICAgICAgICAgICAgZm9yIG9sZF9rIGluIG9sZF9rZXlzOgogICAgICAgICAgICAgICAgICAgIGVudHJ5ID0gdGFyZ2V0LnBvcChvbGRfaykKICAgICAgICAgICAgICAgICAgICBpZiBwa2dfbmFtZSA9PSAiQXp1cmUuSWRlbnRpdHkiOgogICAgICAgICAgICAgICAgICAgICAgICBlbnRyeVsicnVudGltZSJdID0gewogICAgICAgICAgICAgICAgICAgICAgICAgICAgc3BlY1siZGxsX3JlbF9wYXRoIl06IHsKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAiYXNzZW1ibHlWZXJzaW9uIjogc3BlY1siYXNzZW1ibHlfdmVyc2lvbiJdLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICJmaWxlVmVyc2lvbiI6IHNwZWNbImZpbGVfdmVyc2lvbiJdLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgfQogICAgICAgICAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgICAgICAgICAgZWxpZiBwa2dfbmFtZSA9PSAiTWljcm9zb2Z0LkRhdGEuU3FsQ2xpZW50IjoKICAgICAgICAgICAgICAgICAgICAgICAgaWYgImRlcGVuZGVuY2llcyIgaW4gZW50cnkgYW5kICJBenVyZS5JZGVudGl0eSIgaW4gZW50cnlbImRlcGVuZGVuY2llcyJdOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgZW50cnlbImRlcGVuZGVuY2llcyJdWyJBenVyZS5JZGVudGl0eSJdID0gVEFSR0VUX1BBQ0tBR0VTWyJBenVyZS5JZGVudGl0eSJdWyJ0YXJnZXRfdmVyc2lvbl9zdHIiXQogICAgICAgICAgICAgICAgICAgICAgICBlbnRyeVsicnVudGltZVRhcmdldHMiXSA9IHsKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHNwZWNbImRsbF9yZWxfcGF0aCJdOiB7CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgInJpZCI6ICJ1bml4IiwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAiYXNzZXRUeXBlIjogInJ1bnRpbWUiLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICJhc3NlbWJseVZlcnNpb24iOiBzcGVjWyJhc3NlbWJseV92ZXJzaW9uIl0sCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgImZpbGVWZXJzaW9uIjogc3BlY1siZmlsZV92ZXJzaW9uIl0sCiAgICAgICAgICAgICAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgICAgICAgICAgICAgIH0KICAgICAgICAgICAgICAgICAgICBlbGlmIHBrZ19uYW1lID09ICJTeXN0ZW0uRHJhd2luZy5Db21tb24iOgogICAgICAgICAgICAgICAgICAgICAgICBlbnRyeVsicnVudGltZSJdID0gewogICAgICAgICAgICAgICAgICAgICAgICAgICAgc3BlY1siZGxsX3JlbF9wYXRoIl06IHsKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAiYXNzZW1ibHlWZXJzaW9uIjogc3BlY1siYXNzZW1ibHlfdmVyc2lvbiJdLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICJmaWxlVmVyc2lvbiI6IHNwZWNbImZpbGVfdmVyc2lvbiJdLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgfQogICAgICAgICAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgICAgICAgICAgICAgIGVudHJ5LnBvcCgicnVudGltZVRhcmdldHMiLCBOb25lKQoKICAgICAgICAgICAgICAgICAgICB0YXJnZXRbZiJ7cGtnX25hbWV9L3tzcGVjWyd0YXJnZXRfdmVyc2lvbl9zdHInXX0iXSA9IGVudHJ5CiAgICAgICAgICAgICAgICAgICAgbW9kaWZpZWQgPSBUcnVlCgogICAgICAgICAgICAgICAgZm9yIHBrZ19lbnRyeSBpbiB0YXJnZXQudmFsdWVzKCk6CiAgICAgICAgICAgICAgICAgICAgaWYgaXNpbnN0YW5jZShwa2dfZW50cnksIGRpY3QpIGFuZCAiZGVwZW5kZW5jaWVzIiBpbiBwa2dfZW50cnk6CiAgICAgICAgICAgICAgICAgICAgICAgIGRlcHMgPSBwa2dfZW50cnlbImRlcGVuZGVuY2llcyJdCiAgICAgICAgICAgICAgICAgICAgICAgIGlmIHBrZ19uYW1lIGluIGRlcHM6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBkZXBzW3BrZ19uYW1lXSA9IHNwZWNbInRhcmdldF92ZXJzaW9uX3N0ciJdCiAgICAgICAgICAgICAgICAgICAgICAgICAgICBtb2RpZmllZCA9IFRydWUKCiAgICAgICAgICAgIGxpYnMgPSBkLmdldCgibGlicmFyaWVzIiwge30pCiAgICAgICAgICAgIG9sZF9saWJfa2V5cyA9IFtrIGZvciBrIGluIGxpYnMgaWYgay5zdGFydHN3aXRoKGYie3BrZ19uYW1lfS8iKV0KICAgICAgICAgICAgZm9yIG9sZF9rIGluIG9sZF9saWJfa2V5czoKICAgICAgICAgICAgICAgIGxlID0gbGlicy5wb3Aob2xkX2spCiAgICAgICAgICAgICAgICBsZVsicGF0aCJdID0gZiJ7cGtnX25hbWUubG93ZXIoKX0ve3NwZWNbJ3RhcmdldF92ZXJzaW9uX3N0ciddfSIKICAgICAgICAgICAgICAgIGxlWyJoYXNoUGF0aCJdID0gZiJ7cGtnX25hbWUubG93ZXIoKX0ue3NwZWNbJ3RhcmdldF92ZXJzaW9uX3N0ciddfS5udXBrZy5zaGE1MTIiCiAgICAgICAgICAgICAgICBsaWJzW2Yie3BrZ19uYW1lfS97c3BlY1sndGFyZ2V0X3ZlcnNpb25fc3RyJ119Il0gPSBsZQogICAgICAgICAgICAgICAgbW9kaWZpZWQgPSBUcnVlCgogICAgICAgICAgICBpZiBtb2RpZmllZDoKICAgICAgICAgICAgICAgIHdpdGggb3BlbihwLCAidyIsIGVuY29kaW5nPSJ1dGYtOCIpIGFzIGY6CiAgICAgICAgICAgICAgICAgICAganNvbi5kdW1wKGQsIGYsIGluZGVudD0yKQoKICAgIHByaW50KCJTdGFnZSAxOiBEeW5hbWljIHJlbWVkaWF0aW9uIGNoZWNrIGNvbXBsZXRlLiIpCgoKaWYgX19uYW1lX18gPT0gIl9fbWFpbl9fIjoKICAgIHJlbWVkaWF0ZV9hcHBfZGVwZW5kZW5jaWVzKCIvYXBwIikK" | base64 -d | python3


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
        curl -fsSL https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb -o /tmp/cuda-keyring.deb && \
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

# Ensure execution permissions, idempotently neutralize runtime apt-get calls, and inject invariant Real Image marker
RUN chmod +x /app/docker-entrypoint.sh && \
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
