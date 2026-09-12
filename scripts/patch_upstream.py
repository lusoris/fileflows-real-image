#!/usr/bin/env python3
"""
Dynamic Semantic NuGet Vulnerability Remediator for FileFlows Real Image.

- Inspects active versions across all /app/**/*.deps.json files.
- Remediates only what the advisories actually require, so an upstream assembly that is
  already patched is never replaced: min_version is the published fixed version, not the
  latest release. target_version_str is what gets installed when intervention is needed.
- Fails closed: a manifest is only rewritten once the replacement assembly is on disk.
- Resolves CVE-2023-36414, CVE-2024-29992, CVE-2024-35255 (Azure.Identity 1.3.0 -> 1.11.4)
- Resolves CVE-2024-0056 (Microsoft.Data.SqlClient 3.0.0 -> 3.1.5)
- Resolves CVE-2021-24112 (System.Drawing.Common 4.7.0 -> 4.7.2)
- Resolves CVE-2025-6965 (SQLitePCLRaw.lib.e_sqlite3 2.1.11 -> 2.1.12, native per-RID)
"""

import glob
import io
import json
import os
import re
import urllib.request
import zipfile

NUGET_TIMEOUT_SECONDS = 60

# Azure.Identity 1.11.4 needs a newer dependency set than upstream ships, and upgrading the
# assembly without them leaves it unloadable ("Could not load Azure.Core, Version=1.38.0.0").
# Resolved with `dotnet publish` for net10.0 and reduced to what /app does not already
# satisfy: Microsoft.IdentityModel.Abstractions (8.19.1) and
# System.Security.Cryptography.ProtectedData (4.7.0) are already new enough.
AZURE_IDENTITY_CLOSURE = [
    {"name": "Azure.Core", "version": "1.38.0", "asset": "lib/net6.0/Azure.Core.dll"},
    {"name": "Microsoft.Bcl.AsyncInterfaces", "version": "1.1.1",
     "asset": "lib/netstandard2.1/Microsoft.Bcl.AsyncInterfaces.dll"},
    {"name": "Microsoft.Identity.Client", "version": "4.61.3",
     "asset": "lib/net6.0/Microsoft.Identity.Client.dll"},
    {"name": "Microsoft.Identity.Client.Extensions.Msal", "version": "4.61.3",
     "asset": "lib/net6.0/Microsoft.Identity.Client.Extensions.Msal.dll"},
    {"name": "System.ClientModel", "version": "1.0.0", "asset": "lib/net6.0/System.ClientModel.dll"},
    {"name": "System.Memory.Data", "version": "1.0.2", "asset": "lib/netstandard2.0/System.Memory.Data.dll"},
]

TARGET_PACKAGES = {
    "Azure.Identity": {
        # CVE-2023-36414 -> 1.10.2, CVE-2024-29992 -> 1.11.0, CVE-2024-35255 -> 1.11.4
        "advisory_fixed_versions": [(1, 11, 4)],
        # Install the advisory's fixed version, not the newest release: upstream ships
        # 1.3.0, and 1.11.4 keeps the same single netstandard2.0 asset it already
        # references, so only the version metadata changes.
        "target_version_str": "1.11.4",
        "nupkg_url": "https://api.nuget.org/v3-flatcontainer/azure.identity/1.11.4/azure.identity.1.11.4.nupkg",
        "dll_rel_path": "lib/netstandard2.0/Azure.Identity.dll",
        "dll_name": "Azure.Identity.dll",
        # Azure SDK stamps assemblyVersion as major.minor.0.0, so 1.3.0.0 -> 1.11.0.0.
        "assembly_version": "1.11.0.0",
        "closure": AZURE_IDENTITY_CLOSURE,
    },
    "Microsoft.Data.SqlClient": {
        # CVE-2024-0056 was fixed separately on each maintained branch, and
        # CVE-2022-41064 on the 1.x/2.x branches.
        "advisory_fixed_versions": [(1, 1, 4), (2, 1, 7), (3, 1, 5), (4, 0, 5), (5, 1, 3)],
        # 3.1.5 is the fix on upstream's own 3.x branch. Staying on 3.x avoids the 4.0
        # breaking change that flipped the default connection string to Encrypt=true.
        "target_version_str": "3.1.5",
        "nupkg_url": "https://api.nuget.org/v3-flatcontainer/microsoft.data.sqlclient/3.1.5/microsoft.data.sqlclient.3.1.5.nupkg",
        "dll_rel_path": "runtimes/unix/lib/netcoreapp3.1/Microsoft.Data.SqlClient.dll",
        "dll_name": "Microsoft.Data.SqlClient.dll",
        # Unchanged across the 3.x branch; upstream already records 3.0.0.0.
        "assembly_version": None,
    },
    "SQLitePCLRaw.lib.e_sqlite3": {
        # CVE-2025-6965: the bundled SQLite build is vulnerable up to and including
        # 2.1.11, so 2.1.12 is the minimal fix on that branch.
        "advisory_fixed_versions": [(2, 1, 12)],
        "target_version_str": "2.1.12",
        "nupkg_url": "https://api.nuget.org/v3-flatcontainer/sqlitepclraw.lib.e_sqlite3/2.1.12/sqlitepclraw.lib.e_sqlite3.2.1.12.nupkg",
        # A native package: every RID ships its own binary, so each on-disk copy is
        # replaced with the asset published for that same RID rather than one chosen build.
        "asset_kind": "native",
        "dll_rel_path": "runtimes/linux-x64/native/libe_sqlite3.so",
        "dll_name": "libe_sqlite3.so",
        "assembly_version": None,
    },
    "System.Drawing.Common": {
        # CVE-2021-24112 -> 4.7.2 on the 4.x branch, 5.0.3 on the 5.x branch.
        "advisory_fixed_versions": [(4, 7, 2), (5, 0, 3)],
        # 4.7.2 is the fix on upstream's 4.7.x branch. 6.0+ dropped Unix support and
        # 8.0.0 ships no runtimes/unix asset at all, so upgrading that far would trade a
        # working Linux implementation for a Windows-only one.
        "target_version_str": "4.7.2",
        "nupkg_url": "https://api.nuget.org/v3-flatcontainer/system.drawing.common/4.7.2/system.drawing.common.4.7.2.nupkg",
        "dll_rel_path": "runtimes/unix/lib/netcoreapp3.0/System.Drawing.Common.dll",
        "dll_name": "System.Drawing.Common.dll",
        # Unchanged across 4.7.x; upstream records 4.0.0.1 / 4.0.2.0 per asset.
        "assembly_version": None,
    },
}


def parse_version(v_str: str) -> tuple:
    """Parse semantic version string into a comparable tuple of integers."""
    parts = re.findall(r"\d+", v_str.split("-")[0].split("+")[0])
    return tuple(map(int, parts)) if parts else (0,)


def applicable_fix(version: tuple, fixed_versions: list) -> tuple:
    """Return the advisory fix that governs `version`, or None if it is unaffected.

    Advisories for these packages are fixed independently on each maintained branch, so
    a single "minimum safe version" would either miss a vulnerable newer branch or
    condemn an already-patched older one. A version is judged against the fix published
    for its own major line; a major line no advisory ever touched is affected only if it
    predates every fixed branch.
    """
    same_branch = [f for f in fixed_versions if f[0] == version[0]]
    if same_branch:
        required = max(same_branch)
        return required if version < required else None
    oldest = min(fixed_versions)
    return oldest if version < oldest else None


def find_deps_files(app_root: str) -> list:
    """Return every .deps.json under app_root, including ones directly in it."""
    root = app_root.rstrip("/") or "/"
    return sorted(set(glob.glob(f"{glob.escape(root)}/**/*.deps.json", recursive=True)))


def read_file_version(dll_bytes: bytes) -> str:
    """Extract the Win32 FileVersion from a PE's VS_FIXEDFILEINFO block, if present."""
    marker = b"\xbd\x04\xef\xfe"  # VS_FIXEDFILEINFO dwSignature 0xFEEF04BD, little-endian
    offset = dll_bytes.find(marker)
    if offset < 0 or offset + 16 > len(dll_bytes):
        return ""

    def _u32(at):
        return int.from_bytes(dll_bytes[at:at + 4], "little")

    ms, ls = _u32(offset + 8), _u32(offset + 12)
    return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"


def fetch_nupkg(url: str) -> bytes:
    """Download a NuGet package, verifying the response before it is opened."""
    req = urllib.request.Request(url, headers={"User-Agent": "FileFlows-Real-Image/1.0"})
    with urllib.request.urlopen(req, timeout=NUGET_TIMEOUT_SECONDS) as resp:
        status = getattr(resp, "status", None)
        if status is not None and status != 200:
            raise RuntimeError(f"NuGet returned HTTP {status} for {url}")
        payload = resp.read()

    if not payload:
        raise RuntimeError(f"NuGet returned an empty response body for {url}")
    return payload


def fetch_nupkg_dll(url: str, dll_rel_path: str) -> bytes:
    """Download a NuGet package and extract one assembly, verifying every step."""
    with zipfile.ZipFile(io.BytesIO(fetch_nupkg(url))) as archive:
        if dll_rel_path not in archive.namelist():
            raise RuntimeError(f"Asset '{dll_rel_path}' is absent from {url}")
        dll_bytes = archive.read(dll_rel_path)

    if not dll_bytes:
        raise RuntimeError(f"Asset '{dll_rel_path}' is empty in {url}")
    return dll_bytes


def replace_rid_assets(app_root: str, package: bytes, asset_name: str) -> int:
    """Replace each runtimes/<rid>/... copy of asset_name with the package's own build.

    Native packages ship a distinct binary per runtime identifier, so writing one
    chosen build over all of them would put, say, an x64 library in the arm64 slot.
    """
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        assets = {
            name: archive.read(name)
            for name in archive.namelist()
            if name.startswith("runtimes/") and name.endswith("/" + asset_name)
        }
    if not assets:
        raise RuntimeError(f"Package contains no runtimes/**/{asset_name} assets")

    replaced_count = 0
    for root, _, files in os.walk(app_root):
        if asset_name not in files:
            continue
        path = os.path.join(root, asset_name)
        marker = os.sep + "runtimes" + os.sep
        if marker not in path:
            continue
        relative = path[path.rindex(marker) + 1:].replace(os.sep, "/")
        if relative in assets:
            with open(path, "wb") as handle:
                handle.write(assets[relative])
            replaced_count += 1
    return replaced_count


def nuget_url(name: str, version: str) -> str:
    """Flat-container URL for one package version."""
    lower = name.lower()
    return f"https://api.nuget.org/v3-flatcontainer/{lower}/{version}/{lower}.{version}.nupkg"


def host_directories(app_root: str, dll_name: str) -> list:
    """Directories holding dll_name; a dependency's assembly has to sit alongside it."""
    return sorted({root for root, _, files in os.walk(app_root) if dll_name in files})


def references_package(path: str, pkg_name: str) -> bool:
    """True if this manifest declares pkg_name in any target."""
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    for target in document.get("targets", {}).values():
        if isinstance(target, dict) and any(k.startswith(f"{pkg_name}/") for k in target):
            return True
    return False


def upsert_package_entry(document: dict, member: dict, file_version: str) -> bool:
    """Re-key or add one closure member, leaving any other metadata on the entry intact."""
    name, version = member["name"], member["version"]
    key = f"{name}/{version}"
    asset = {"fileVersion": file_version} if file_version else {}

    for target in document.get("targets", {}).values():
        if not isinstance(target, dict):
            continue
        entry = {}
        for old_key in [k for k in target if k.startswith(f"{name}/")]:
            existing = target.pop(old_key)
            if isinstance(existing, dict):
                entry = existing
        entry["runtime"] = {member["asset"]: asset}
        target[key] = entry
        for pkg_entry in target.values():
            if isinstance(pkg_entry, dict) and name in pkg_entry.get("dependencies", {}):
                pkg_entry["dependencies"][name] = version

    libraries = document.get("libraries")
    if isinstance(libraries, dict):
        library = {}
        for old_key in [k for k in libraries if k.startswith(f"{name}/")]:
            existing = libraries.pop(old_key)
            if isinstance(existing, dict):
                library = existing
        library.update({
            "type": "package", "serviceable": True, "sha512": "",
            "path": f"{name.lower()}/{version}",
            "hashPath": f"{name.lower()}.{version}.nupkg.sha512",
        })
        libraries[key] = library
    return True


def install_closure(app_root: str, deps_files: list, pkg_name: str, spec: dict) -> None:
    """Install the dependency set the upgraded package needs but upstream does not ship."""
    closure = spec.get("closure") or []
    if not closure:
        return

    host_dirs = host_directories(app_root, spec["dll_name"])
    manifests = [p for p in deps_files if references_package(p, pkg_name)]

    for member in closure:
        dll_bytes = fetch_nupkg_dll(nuget_url(member["name"], member["version"]), member["asset"])
        file_version = read_file_version(dll_bytes)
        for directory in host_dirs:
            with open(os.path.join(directory, f"{member['name']}.dll"), "wb") as handle:
                handle.write(dll_bytes)
        for path in manifests:
            with open(path, "r", encoding="utf-8") as handle:
                document = json.load(handle)
            upsert_package_entry(document, member, file_version)
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(document, handle, indent=2)
        print(f"--> Closure: {member['name']} {member['version']} -> {len(host_dirs)} app dir(s)")


def scan_package(deps_files: list, pkg_name: str, fixed_versions: list) -> tuple:
    """Return (found_any, required_fix, discovered_versions) for pkg_name."""
    found_any = False
    required_fix = None
    discovered_versions = set()

    for path in deps_files:
        with open(path, "r", encoding="utf-8") as handle:
            document = json.load(handle)
        for target in document.get("targets", {}).values():
            if not isinstance(target, dict):
                continue
            for key in target:
                if key.startswith(f"{pkg_name}/"):
                    found_any = True
                    v_str = key.split("/", 1)[1]
                    discovered_versions.add(v_str)
                    fix = applicable_fix(parse_version(v_str), fixed_versions)
                    if fix and (required_fix is None or fix > required_fix):
                        required_fix = fix

    return found_any, required_fix, discovered_versions


def replace_assembly(app_root: str, dll_name: str, dll_bytes: bytes) -> int:
    """Overwrite every copy of dll_name beneath app_root; return how many were written."""
    replaced_count = 0
    for root, _, files in os.walk(app_root):
        if dll_name in files:
            dll_path = os.path.join(root, dll_name)
            with open(dll_path, "wb") as handle:
                handle.write(dll_bytes)
            replaced_count += 1
    return replaced_count


def refresh_entry_assets(entry: dict, pkg_name: str, spec: dict) -> dict:
    """Refresh version metadata in place, preserving upstream's own asset layout.

    The install target ships the same asset paths upstream already references, so the
    entry's runtime/runtimeTargets keys stay exactly as published; only the versions
    they advertise change. Rewriting the paths would be guesswork about the layout.
    """
    if pkg_name == "Microsoft.Data.SqlClient":
        dependencies = entry.get("dependencies", {})
        if "Azure.Identity" in dependencies:
            dependencies["Azure.Identity"] = TARGET_PACKAGES["Azure.Identity"]["target_version_str"]

    file_version = spec.get("observed_file_version")
    assembly_version = spec.get("assembly_version")

    for section in ("runtime", "runtimeTargets"):
        assets = entry.get(section)
        if not isinstance(assets, dict):
            continue
        for meta in assets.values():
            if not isinstance(meta, dict):
                continue
            if file_version:
                meta["fileVersion"] = file_version
            if assembly_version:
                meta["assemblyVersion"] = assembly_version

    return entry


def patch_targets(document: dict, pkg_name: str, spec: dict) -> bool:
    """Re-key and rewrite every target entry and dependency range for pkg_name."""
    modified = False
    new_key = f"{pkg_name}/{spec['target_version_str']}"

    for target in document.get("targets", {}).values():
        if not isinstance(target, dict):
            continue

        for old_key in [k for k in target if k.startswith(f"{pkg_name}/")]:
            entry = target.pop(old_key)
            if isinstance(entry, dict):
                entry = refresh_entry_assets(entry, pkg_name, spec)
            target[new_key] = entry
            modified = True

        for pkg_entry in target.values():
            if isinstance(pkg_entry, dict) and pkg_name in pkg_entry.get("dependencies", {}):
                pkg_entry["dependencies"][pkg_name] = spec["target_version_str"]
                modified = True

    return modified


def patch_libraries(document: dict, pkg_name: str, spec: dict) -> bool:
    """Re-key the libraries section and drop the now-stale package hash."""
    modified = False
    libraries = document.get("libraries", {})
    version = spec["target_version_str"]

    for old_key in [k for k in libraries if k.startswith(f"{pkg_name}/")]:
        library = libraries.pop(old_key)
        if isinstance(library, dict):
            library["path"] = f"{pkg_name.lower()}/{version}"
            library["hashPath"] = f"{pkg_name.lower()}.{version}.nupkg.sha512"
            # The recorded hash belongs to the superseded package; keeping it would
            # assert an integrity value that no longer matches the shipped assembly.
            if "sha512" in library:
                library["sha512"] = ""
        libraries[f"{pkg_name}/{version}"] = library
        modified = True

    return modified


def patch_deps_file(path: str, pkg_name: str, spec: dict) -> bool:
    """Apply target and library rewrites to a single .deps.json; return True if written."""
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)

    modified = patch_targets(document, pkg_name, spec)
    modified = patch_libraries(document, pkg_name, spec) or modified

    if modified:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2)
    return modified


def upgrade_package(app_root: str, deps_files: list, pkg_name: str, discovered: set) -> None:
    """Fetch, install and record the safe version of one vulnerable package."""
    spec = TARGET_PACKAGES[pkg_name]
    target = parse_version(spec["target_version_str"])
    newest = max((parse_version(v) for v in discovered), default=target)
    if newest > target:
        raise RuntimeError(
            f"{pkg_name}: upstream ships {max(discovered, key=parse_version)} but this policy only "
            f"pins {spec['target_version_str']}. Installing it would be a downgrade; the pinned "
            "target needs updating to the fix on upstream's current branch."
        )
    print(f"--> Fetching {pkg_name} {spec['target_version_str']} from NuGet...")

    if spec.get("asset_kind") == "native":
        replaced_count = replace_rid_assets(app_root, fetch_nupkg(spec["nupkg_url"]), spec["dll_name"])
    else:
        dll_bytes = fetch_nupkg_dll(spec["nupkg_url"], spec["dll_rel_path"])
        # Record what the assembly reports; there is no hardcoded literal to drift.
        spec["observed_file_version"] = read_file_version(dll_bytes)
        replaced_count = replace_assembly(app_root, spec["dll_name"], dll_bytes)

    if replaced_count == 0:
        raise RuntimeError(
            f"{pkg_name}: '{spec['dll_name']}' is declared in a .deps.json but no copy exists "
            f"under {app_root}. Refusing to record {spec['target_version_str']} in the manifest, "
            "which would report a patched version while the vulnerable assembly remains."
        )
    print(f"--> Replaced {replaced_count} instance(s) of {spec['dll_name']} in {app_root}")

    for path in deps_files:
        patch_deps_file(path, pkg_name, spec)

    install_closure(app_root, deps_files, pkg_name, spec)


def remediate_app_dependencies(app_root: str = "/app") -> None:
    """Scan and conditionally remediate vulnerable NuGet packages in app_root."""
    deps_files = find_deps_files(app_root)
    packages_to_upgrade = []

    for pkg_name, spec in TARGET_PACKAGES.items():
        found_any, required_fix, versions = scan_package(
            deps_files, pkg_name, spec["advisory_fixed_versions"]
        )
        v_list = ", ".join(sorted(versions))

        if not found_any:
            print(f"[UPSTREAM CLEAN] {pkg_name}: Not present in upstream dependencies. Skipped.")
        elif required_fix is None:
            print(
                f"[UPSTREAM CLEAN] {pkg_name}: Upstream version(s) ({v_list}) are at or past the fix published for their branch. No patch needed."
            )
        else:
            fix_str = ".".join(str(n) for n in required_fix)
            print(
                f"[REMEDIATE] {pkg_name}: Upstream version(s) ({v_list}) predate the branch fix {fix_str}. Upgrading to {spec['target_version_str']}..."
            )
            packages_to_upgrade.append((pkg_name, versions))

    for pkg_name, versions in packages_to_upgrade:
        upgrade_package(app_root, deps_files, pkg_name, versions)

    print("Stage 1: Dynamic remediation check complete.")


if __name__ == "__main__":
    remediate_app_dependencies("/app")
