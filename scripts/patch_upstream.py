#!/usr/bin/env python3
"""
Dynamic Semantic NuGet Vulnerability Remediator for FileFlows Real Image.

- Inspects active versions across all /app/**/*.deps.json files.
- If upstream has already upgraded to or beyond safe minimum versions, preserves upstream (no downgrade).
- If packages are vulnerable or older than safe minimums, upgrades assembly and patches .deps.json.
- Resolves CVE-2023-36414, CVE-2024-29992, CVE-2024-35255 (Azure.Identity < 1.21.0)
- Resolves CVE-2024-0056 (Microsoft.Data.SqlClient < 5.2.2)
- Resolves CVE-2021-24112 (System.Drawing.Common < 8.0.0)
"""

import glob
import io
import json
import os
import re
import urllib.request
import zipfile

TARGET_PACKAGES = {
    "Azure.Identity": {
        "min_version": (1, 21, 0),
        "target_version_str": "1.21.0",
        "nupkg_url": "https://api.nuget.org/v3-flatcontainer/azure.identity/1.21.0/azure.identity.1.21.0.nupkg",
        "dll_rel_path": "lib/net10.0/Azure.Identity.dll",
        "dll_name": "Azure.Identity.dll",
        "assembly_version": "1.21.0.0",
        "file_version": "1.2100.26.11501",
    },
    "Microsoft.Data.SqlClient": {
        "min_version": (5, 2, 2),
        "target_version_str": "5.2.2",
        "nupkg_url": "https://api.nuget.org/v3-flatcontainer/microsoft.data.sqlclient/5.2.2/microsoft.data.sqlclient.5.2.2.nupkg",
        "dll_rel_path": "runtimes/unix/lib/net8.0/Microsoft.Data.SqlClient.dll",
        "dll_name": "Microsoft.Data.SqlClient.dll",
        "assembly_version": "5.0.0.0",
        "file_version": "5.202.24263.2",
    },
    "System.Drawing.Common": {
        "min_version": (8, 0, 0),
        "target_version_str": "8.0.0",
        "nupkg_url": "https://api.nuget.org/v3-flatcontainer/system.drawing.common/8.0.0/system.drawing.common.8.0.0.nupkg",
        "dll_rel_path": "lib/netstandard2.0/System.Drawing.Common.dll",
        "dll_name": "System.Drawing.Common.dll",
        "assembly_version": "8.0.0.0",
        "file_version": "8.0.23.53105",
    },
}


def parse_version(v_str: str) -> tuple:
    """Parse semantic version string into a comparable tuple of integers."""
    parts = re.findall(r"\d+", v_str.split("-")[0])
    return tuple(map(int, parts)) if parts else (0,)


def fetch_nupkg(url: str) -> zipfile.ZipFile:
    """Download and open a NuGet package zip file from a URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "FileFlows-Real-Image/1.0"})
    with urllib.request.urlopen(req) as resp:
        return zipfile.ZipFile(io.BytesIO(resp.read()))


def remediate_app_dependencies(app_root: str = "/app") -> None:
    """Scan and conditionally remediate vulnerable NuGet packages in app_root."""
    deps_files = sorted(glob.glob(f"{app_root}/**/*.deps.json", recursive=True))
    packages_to_upgrade = set()

    for pkg_name, spec in TARGET_PACKAGES.items():
        found_any = False
        needs_upgrade = False
        discovered_versions = set()

        for p in deps_files:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            for target in d.get("targets", {}).values():
                for key in target:
                    if key.startswith(f"{pkg_name}/"):
                        found_any = True
                        v_str = key.split("/")[1]
                        discovered_versions.add(v_str)
                        if parse_version(v_str) < spec["min_version"]:
                            needs_upgrade = True

        if not found_any:
            print(f"[UPSTREAM CLEAN] {pkg_name}: Not present in upstream dependencies. Skipped.")
        elif not needs_upgrade:
            v_list = ", ".join(sorted(discovered_versions))
            print(
                f"[UPSTREAM CLEAN] {pkg_name}: Upstream version(s) ({v_list}) meet or exceed target safe version ({spec['target_version_str']}). No patch needed."
            )
        else:
            v_list = ", ".join(sorted(discovered_versions))
            print(
                f"[REMEDIATE] {pkg_name}: Upstream version(s) ({v_list}) below safe threshold ({spec['target_version_str']}). Upgrading..."
            )
            packages_to_upgrade.add(pkg_name)

    for pkg_name in packages_to_upgrade:
        spec = TARGET_PACKAGES[pkg_name]
        print(f"--> Fetching {pkg_name} {spec['target_version_str']} from NuGet...")
        z = fetch_nupkg(spec["nupkg_url"])
        dll_bytes = z.read(spec["dll_rel_path"])

        replaced_count = 0
        for root, _, files in os.walk(app_root):
            if spec["dll_name"] in files:
                dll_path = os.path.join(root, spec["dll_name"])
                with open(dll_path, "wb") as f:
                    f.write(dll_bytes)
                replaced_count += 1
        print(f"--> Replaced {replaced_count} instance(s) of {spec['dll_name']} in {app_root}")

        for p in deps_files:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)

            modified = False
            for target in d.get("targets", {}).values():
                old_keys = [k for k in target if k.startswith(f"{pkg_name}/")]
                for old_k in old_keys:
                    entry = target.pop(old_k)
                    if pkg_name == "Azure.Identity":
                        entry["runtime"] = {
                            spec["dll_rel_path"]: {
                                "assemblyVersion": spec["assembly_version"],
                                "fileVersion": spec["file_version"],
                            }
                        }
                    elif pkg_name == "Microsoft.Data.SqlClient":
                        if "dependencies" in entry and "Azure.Identity" in entry["dependencies"]:
                            entry["dependencies"]["Azure.Identity"] = TARGET_PACKAGES["Azure.Identity"]["target_version_str"]
                        entry["runtimeTargets"] = {
                            spec["dll_rel_path"]: {
                                "rid": "unix",
                                "assetType": "runtime",
                                "assemblyVersion": spec["assembly_version"],
                                "fileVersion": spec["file_version"],
                            }
                        }
                    elif pkg_name == "System.Drawing.Common":
                        entry["runtime"] = {
                            spec["dll_rel_path"]: {
                                "assemblyVersion": spec["assembly_version"],
                                "fileVersion": spec["file_version"],
                            }
                        }
                        entry.pop("runtimeTargets", None)

                    target[f"{pkg_name}/{spec['target_version_str']}"] = entry
                    modified = True

                for pkg_entry in target.values():
                    if isinstance(pkg_entry, dict) and "dependencies" in pkg_entry:
                        deps = pkg_entry["dependencies"]
                        if pkg_name in deps:
                            deps[pkg_name] = spec["target_version_str"]
                            modified = True

            libs = d.get("libraries", {})
            old_lib_keys = [k for k in libs if k.startswith(f"{pkg_name}/")]
            for old_k in old_lib_keys:
                le = libs.pop(old_k)
                le["path"] = f"{pkg_name.lower()}/{spec['target_version_str']}"
                le["hashPath"] = f"{pkg_name.lower()}.{spec['target_version_str']}.nupkg.sha512"
                libs[f"{pkg_name}/{spec['target_version_str']}"] = le
                modified = True

            if modified:
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(d, f, indent=2)

    print("Stage 1: Dynamic remediation check complete.")


if __name__ == "__main__":
    remediate_app_dependencies("/app")
