"""
Unit tests for the dynamic semantic NuGet vulnerability remediator.
Verifies idempotent behavior, absence of downgrades, clean skipping, and that the
remediation path never records a safe version it did not actually install.
"""

import io
import json
from pathlib import Path
import sys
import zipfile

import pytest

# Add scripts directory to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import patch_upstream  # noqa: E402

FRAMEWORK = ".NETCoreApp,Version=v10.0"
FAKE_DLL = b"MZ\x90\x00fake-remediated-assembly"


def write_deps(tmp_path, targets, libraries, name="App.deps.json"):
    """Write a minimal .deps.json fixture and return its path."""
    document = {
        "runtimeTarget": {"name": FRAMEWORK},
        "targets": {FRAMEWORK: targets},
        "libraries": libraries,
    }
    deps_file = tmp_path / name
    deps_file.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return deps_file


def read_deps(deps_file):
    """Read back a .deps.json fixture as (targets, libraries)."""
    document = json.loads(deps_file.read_text(encoding="utf-8"))
    return document["targets"][FRAMEWORK], document["libraries"]


def _pe_with_version(ms, ls):
    """Build a byte blob carrying a VS_FIXEDFILEINFO block with the given version words."""
    return (
        b"\x00" * 64
        + b"\xbd\x04\xef\xfe"              # dwSignature 0xFEEF04BD
        + (0x00010000).to_bytes(4, "little")  # dwStrucVersion
        + ms.to_bytes(4, "little")            # dwFileVersionMS
        + ls.to_bytes(4, "little")            # dwFileVersionLS
        + b"\x00" * 32
    )


def stub_fetch(monkeypatch, payload=FAKE_DLL):
    """Replace the NuGet download with a deterministic in-process stub."""
    calls = []

    def _fetch(url, dll_rel_path):
        calls.append((url, dll_rel_path))
        return payload

    monkeypatch.setattr(patch_upstream, "fetch_nupkg_dll", _fetch)
    return calls


class TestPatchUpstream:
    def test_parse_version(self):
        """Verify semantic version string parsing."""
        assert patch_upstream.parse_version("1.21.0") == (1, 21, 0)
        assert patch_upstream.parse_version("1.22.0") == (1, 22, 0)
        assert patch_upstream.parse_version("5.2.2") == (5, 2, 2)
        assert patch_upstream.parse_version("5.202.24263.2") == (5, 202, 24263, 2)
        assert patch_upstream.parse_version("8.0.0-preview.1") == (8, 0, 0)
        assert patch_upstream.parse_version("8.0.0+build.55") == (8, 0, 0)
        assert patch_upstream.parse_version("unknown") == (0,)

    def test_version_comparisons(self):
        """Thresholds sit exactly at the published fixed version of each advisory."""
        # Azure.Identity: CVE-2024-35255 fixed in 1.11.4 (the highest of its three advisories)
        assert patch_upstream.parse_version("1.11.3") < (1, 11, 4)
        assert patch_upstream.parse_version("1.11.4") >= (1, 11, 4)
        assert patch_upstream.parse_version("1.21.0") >= (1, 11, 4)

        # Microsoft.Data.SqlClient: CVE-2024-0056 fixed in 5.1.3 on the 5.x branch
        assert patch_upstream.parse_version("5.1.2") < (5, 1, 3)
        assert patch_upstream.parse_version("5.1.3") >= (5, 1, 3)
        assert patch_upstream.parse_version("5.2.2") >= (5, 1, 3)

        # System.Drawing.Common: CVE-2021-24112 fixed in 4.7.2 on the 4.x branch
        assert patch_upstream.parse_version("4.7.1") < (4, 7, 2)
        assert patch_upstream.parse_version("4.7.2") >= (4, 7, 2)
        assert patch_upstream.parse_version("8.0.0") >= (4, 7, 2)

    def test_targets_are_the_branch_fix_for_what_upstream_ships(self):
        """Each package installs exactly the advisory fix for upstream's own branch."""
        # Upstream revenz/fileflows:latest ships these versions; the pinned target must be
        # the fix on that same major line, never a jump to a newer branch.
        upstream = {"Azure.Identity": "1.3.0", "Microsoft.Data.SqlClient": "3.0.0",
                    "System.Drawing.Common": "4.7.0", "SQLitePCLRaw.lib.e_sqlite3": "2.1.11"}
        for pkg, spec in patch_upstream.TARGET_PACKAGES.items():
            target = patch_upstream.parse_version(spec["target_version_str"])
            shipped = patch_upstream.parse_version(upstream[pkg])

            assert target[0] == shipped[0], (
                f"{pkg} would move upstream off its {shipped[0]}.x branch to {spec['target_version_str']}"
            )
            assert patch_upstream.applicable_fix(shipped, spec["advisory_fixed_versions"]) == target, (
                f"{pkg} target {spec['target_version_str']} is not the advisory fix for {upstream[pkg]}"
            )
            assert patch_upstream.applicable_fix(target, spec["advisory_fixed_versions"]) is None, (
                f"{pkg} installs {spec['target_version_str']}, which its own policy still flags"
            )
            assert spec["nupkg_url"].endswith(f"{spec['target_version_str']}.nupkg")

    def test_refuses_to_downgrade_a_newer_branch(self, tmp_path, monkeypatch):
        """If upstream moves past the pinned target, fail rather than install an older build."""
        stub_fetch(monkeypatch)
        write_deps(
            tmp_path,
            {"System.Drawing.Common/5.0.1": {"runtime": {"lib/netstandard2.0/System.Drawing.Common.dll": {}}}},
            {"System.Drawing.Common/5.0.1": {}},
        )
        (tmp_path / "System.Drawing.Common.dll").write_bytes(b"old")

        # 5.0.1 predates its own branch fix (5.0.3), so remediation is required, but the
        # pinned target is 4.7.2 and installing it would move upstream backwards.
        with pytest.raises(RuntimeError, match="would be a downgrade"):
            patch_upstream.remediate_app_dependencies(str(tmp_path))

    def test_find_deps_files_includes_root_and_nested(self, tmp_path):
        """Discovery must cover manifests directly in app_root and in subdirectories."""
        (tmp_path / "Server").mkdir()
        root_deps = write_deps(tmp_path, {}, {})
        nested_deps = write_deps(tmp_path / "Server", {}, {}, name="Server.deps.json")

        for app_root in (str(tmp_path), str(tmp_path) + "/"):
            found = patch_upstream.find_deps_files(app_root)
            assert str(root_deps) in found, f"root manifest missed for {app_root!r}"
            assert str(nested_deps) in found, f"nested manifest missed for {app_root!r}"
            assert len(found) == 2, f"unexpected duplicates: {found}"

    def test_skips_when_upstream_already_clean(self, tmp_path, capsys):
        """Verify remediator does not downgrade or modify clean upstream dependencies."""
        deps_file = write_deps(
            tmp_path,
            {
                "Azure.Identity/1.22.0": {"runtime": {"lib/net10.0/Azure.Identity.dll": {}}},
                "Microsoft.Data.SqlClient/5.3.0": {
                    "runtimeTargets": {"runtimes/unix/lib/net8.0/Microsoft.Data.SqlClient.dll": {}}
                },
                "System.Drawing.Common/8.0.1": {
                    "runtime": {"lib/netstandard2.0/System.Drawing.Common.dll": {}}
                },
            },
            {
                "Azure.Identity/1.22.0": {},
                "Microsoft.Data.SqlClient/5.3.0": {},
                "System.Drawing.Common/8.0.1": {},
            },
        )

        patch_upstream.remediate_app_dependencies(str(tmp_path))

        captured = capsys.readouterr().out
        assert "[UPSTREAM CLEAN] Azure.Identity" in captured
        assert "[UPSTREAM CLEAN] Microsoft.Data.SqlClient" in captured
        assert "[UPSTREAM CLEAN] System.Drawing.Common" in captured
        assert "No patch needed" in captured

        # Verify no downgrade occurred in .deps.json
        targets, _ = read_deps(deps_file)
        assert "Azure.Identity/1.22.0" in targets
        assert "Microsoft.Data.SqlClient/5.3.0" in targets
        assert "System.Drawing.Common/8.0.1" in targets

    def test_preserves_patched_but_older_upstream_versions(self, tmp_path, capsys):
        """Versions that are patched but older than the install target are left untouched.

        These are exactly the cases the previous latest-release thresholds replaced
        needlessly: each version below is already clear of every published advisory.
        """
        deps_file = write_deps(
            tmp_path,
            {
                "Azure.Identity/1.11.4": {"runtime": {"lib/net6.0/Azure.Identity.dll": {}}},
                "Microsoft.Data.SqlClient/5.1.3": {"runtime": {"lib/net6.0/Microsoft.Data.SqlClient.dll": {}}},
                "System.Drawing.Common/4.7.2": {"runtime": {"lib/netstandard2.0/System.Drawing.Common.dll": {}}},
            },
            {
                "Azure.Identity/1.11.4": {},
                "Microsoft.Data.SqlClient/5.1.3": {},
                "System.Drawing.Common/4.7.2": {},
            },
        )
        for name in ("Azure.Identity.dll", "Microsoft.Data.SqlClient.dll", "System.Drawing.Common.dll"):
            (tmp_path / name).write_bytes(b"upstream-original")

        patch_upstream.remediate_app_dependencies(str(tmp_path))

        captured = capsys.readouterr().out
        assert "[REMEDIATE]" not in captured, f"needlessly replaced an already-patched assembly:\n{captured}"
        assert captured.count("No patch needed") == 3

        targets, _ = read_deps(deps_file)
        assert "Azure.Identity/1.11.4" in targets
        assert "Microsoft.Data.SqlClient/5.1.3" in targets
        assert "System.Drawing.Common/4.7.2" in targets
        for name in ("Azure.Identity.dll", "Microsoft.Data.SqlClient.dll", "System.Drawing.Common.dll"):
            assert (tmp_path / name).read_bytes() == b"upstream-original", f"{name} was overwritten"

    def test_skips_when_packages_not_present(self, tmp_path, capsys):
        """Verify remediator cleanly skips packages absent in upstream dependencies."""
        write_deps(tmp_path, {"Newtonsoft.Json/13.0.3": {}}, {"Newtonsoft.Json/13.0.3": {}})

        patch_upstream.remediate_app_dependencies(str(tmp_path))

        captured = capsys.readouterr().out
        assert "[UPSTREAM CLEAN] Azure.Identity: Not present in upstream dependencies. Skipped." in captured
        assert "[UPSTREAM CLEAN] Microsoft.Data.SqlClient: Not present in upstream dependencies. Skipped." in captured
        assert "[UPSTREAM CLEAN] System.Drawing.Common: Not present in upstream dependencies. Skipped." in captured


class TestRemediationPath:
    """Assertions covering the upgrade branch that actually rewrites the image."""

    def test_upgrades_vulnerable_package(self, tmp_path, monkeypatch, capsys):
        """A below-threshold package is re-keyed and physically replaced, layout intact."""
        calls = stub_fetch(monkeypatch)
        deps_file = write_deps(
            tmp_path,
            {
                # Exactly how upstream declares System.Drawing.Common/4.7.0.
                "System.Drawing.Common/4.7.0": {
                    "runtime": {
                        "lib/netstandard2.0/System.Drawing.Common.dll":
                            {"assemblyVersion": "4.0.0.1", "fileVersion": "4.6.26919.2"}
                    },
                    "runtimeTargets": {
                        "runtimes/unix/lib/netcoreapp3.0/System.Drawing.Common.dll":
                            {"rid": "unix", "assetType": "runtime",
                             "assemblyVersion": "4.0.2.0", "fileVersion": "4.700.19.56404"}
                    },
                },
                "SomeApp/1.0.0": {"dependencies": {"System.Drawing.Common": "4.7.0"}},
            },
            {"System.Drawing.Common/4.7.0": {"type": "package", "sha512": "sha512-STALE==", "path": "x"}},
        )
        dll = tmp_path / "System.Drawing.Common.dll"
        dll.write_bytes(b"vulnerable-original")

        patch_upstream.remediate_app_dependencies(str(tmp_path))

        assert dll.read_bytes() == FAKE_DLL, "vulnerable assembly was not overwritten on disk"
        assert len(calls) == 1, f"expected exactly one NuGet fetch, got {calls}"

        targets, libraries = read_deps(deps_file)
        assert "System.Drawing.Common/4.7.2" in targets
        assert "System.Drawing.Common/4.7.0" not in targets
        entry = targets["System.Drawing.Common/4.7.2"]

        # Upstream's own asset layout survives the patch untouched.
        assert list(entry["runtime"]) == ["lib/netstandard2.0/System.Drawing.Common.dll"]
        assert list(entry["runtimeTargets"]) == ["runtimes/unix/lib/netcoreapp3.0/System.Drawing.Common.dll"]
        assert entry["runtimeTargets"]["runtimes/unix/lib/netcoreapp3.0/System.Drawing.Common.dll"]["rid"] == "unix"
        # assembly_version is None for this package, so upstream's per-asset values stand.
        assert entry["runtime"]["lib/netstandard2.0/System.Drawing.Common.dll"]["assemblyVersion"] == "4.0.0.1"
        assert entry["runtimeTargets"]["runtimes/unix/lib/netcoreapp3.0/System.Drawing.Common.dll"]["assemblyVersion"] == "4.0.2.0"

        assert targets["SomeApp/1.0.0"]["dependencies"]["System.Drawing.Common"] == "4.7.2"
        assert "System.Drawing.Common/4.7.2" in libraries
        assert libraries["System.Drawing.Common/4.7.2"]["sha512"] == "", "stale package hash was retained"
        assert "[REMEDIATE] System.Drawing.Common" in capsys.readouterr().out

    def test_refuses_to_record_version_it_did_not_install(self, tmp_path, monkeypatch):
        """Fail closed: never claim a patched version when no assembly was replaced."""
        stub_fetch(monkeypatch)
        deps_file = write_deps(
            tmp_path,
            {"System.Drawing.Common/4.7.0": {"runtime": {"lib/netstandard2.0/System.Drawing.Common.dll": {}}}},
            {"System.Drawing.Common/4.7.0": {"sha512": "sha512-STALE=="}},
        )
        # No System.Drawing.Common.dll anywhere under tmp_path.

        with pytest.raises(RuntimeError, match="no copy exists"):
            patch_upstream.remediate_app_dependencies(str(tmp_path))

        targets, libraries = read_deps(deps_file)
        assert "System.Drawing.Common/4.7.0" in targets, "manifest was rewritten despite no replacement"
        assert "System.Drawing.Common/4.7.2" not in targets, "manifest falsely claims a patched version"
        assert libraries["System.Drawing.Common/4.7.0"]["sha512"] == "sha512-STALE=="

    def test_sqlclient_keeps_layout_and_bumps_its_azure_dependency(self, tmp_path, monkeypatch):
        """SqlClient keeps every published asset path; only versions and the dep range move."""
        stub_fetch(monkeypatch, payload=_pe_with_version((3 << 16) | 1, (5 << 16) | 0))
        deps_file = write_deps(
            tmp_path,
            {
                "Microsoft.Data.SqlClient/3.0.0": {
                    "dependencies": {"Azure.Identity": "1.3.0"},
                    "runtime": {"lib/netcoreapp3.1/Microsoft.Data.SqlClient.dll":
                                {"assemblyVersion": "3.0.0.0", "fileVersion": "3.0.0.0"}},
                    "runtimeTargets": {
                        "runtimes/unix/lib/netcoreapp3.1/Microsoft.Data.SqlClient.dll":
                            {"rid": "unix", "assetType": "runtime",
                             "assemblyVersion": "3.0.0.0", "fileVersion": "3.0.0.0"},
                    },
                }
            },
            {"Microsoft.Data.SqlClient/3.0.0": {"sha512": "sha512-STALE=="}},
        )
        (tmp_path / "Microsoft.Data.SqlClient.dll").write_bytes(b"old")

        patch_upstream.remediate_app_dependencies(str(tmp_path))

        entry = read_deps(deps_file)[0]["Microsoft.Data.SqlClient/3.1.5"]
        assert entry["dependencies"]["Azure.Identity"] == "1.11.4"
        assert list(entry["runtime"]) == ["lib/netcoreapp3.1/Microsoft.Data.SqlClient.dll"]
        assert list(entry["runtimeTargets"]) == ["runtimes/unix/lib/netcoreapp3.1/Microsoft.Data.SqlClient.dll"]
        for section in ("runtime", "runtimeTargets"):
            for meta in entry[section].values():
                assert meta["fileVersion"] == "3.1.5.0", "fileVersion not refreshed from the assembly"
                assert meta["assemblyVersion"] == "3.0.0.0", "assemblyVersion must stay on the 3.x line"

    def test_remediation_is_idempotent(self, tmp_path, monkeypatch, capsys):
        """A second pass over an already-patched tree performs no further downloads."""
        calls = stub_fetch(monkeypatch)
        write_deps(
            tmp_path,
            {"System.Drawing.Common/4.7.0": {"runtime": {"lib/netstandard2.0/System.Drawing.Common.dll": {}}}},
            {"System.Drawing.Common/4.7.0": {"sha512": "sha512-STALE=="}},
        )
        (tmp_path / "System.Drawing.Common.dll").write_bytes(b"vulnerable-original")

        patch_upstream.remediate_app_dependencies(str(tmp_path))
        assert len(calls) == 1
        capsys.readouterr()

        patch_upstream.remediate_app_dependencies(str(tmp_path))
        assert len(calls) == 1, "second run re-downloaded an already-patched package"
        assert "No patch needed" in capsys.readouterr().out


class TestFileVersionExtraction:
    """Assertions on reading the Win32 FileVersion out of a PE assembly."""

    def test_reads_four_part_file_version(self):
        """The four version words decode to major.minor.build.revision."""
        blob = _pe_with_version((8 << 16) | 0, (23 << 16) | 53105)
        assert patch_upstream.read_file_version(blob) == "8.0.23.53105"

        blob = _pe_with_version((1 << 16) | 2100, (26 << 16) | 21009)
        assert patch_upstream.read_file_version(blob) == "1.2100.26.21009"

    def test_returns_empty_when_no_version_block(self):
        """An assembly with no VS_FIXEDFILEINFO yields '' rather than a bogus version."""
        assert patch_upstream.read_file_version(b"\x00" * 512) == ""
        assert patch_upstream.read_file_version(b"") == ""

    def test_truncated_version_block_is_rejected(self):
        """A signature at the very end of the buffer must not read past it."""
        assert patch_upstream.read_file_version(b"\x00" * 16 + b"\xbd\x04\xef\xfe") == ""

    def test_recorded_version_comes_from_the_assembly(self, tmp_path, monkeypatch):
        """The recorded fileVersion is read from the installed assembly, not from a literal."""
        monkeypatch.setattr(patch_upstream, "fetch_nupkg_dll",
                            lambda url, path: _pe_with_version((9 << 16) | 9, (9 << 16) | 9))
        write_deps(
            tmp_path,
            {"System.Drawing.Common/4.7.0": {"runtime": {"lib/netstandard2.0/System.Drawing.Common.dll":
                                                        {"fileVersion": "4.6.26919.2"}}}},
            {"System.Drawing.Common/4.7.0": {"sha512": "sha512-STALE=="}},
        )
        (tmp_path / "System.Drawing.Common.dll").write_bytes(b"old")
        deps_file = tmp_path / "App.deps.json"

        patch_upstream.remediate_app_dependencies(str(tmp_path))

        entry = read_deps(deps_file)[0]["System.Drawing.Common/4.7.2"]
        asset = list(entry["runtime"].values())[0]
        assert asset["fileVersion"] == "9.9.9.9", "recorded fileVersion did not come from the assembly"


class TestMalformedInput:
    """The remediator must tolerate manifests that do not match the expected shape."""

    def test_ignores_non_dict_targets_and_entries(self, tmp_path, capsys):
        """A malformed manifest is skipped, not crashed on."""
        deps_file = tmp_path / "Broken.deps.json"
        deps_file.write_text(json.dumps({
            "targets": {
                "bad-target-is-a-list": ["System.Drawing.Common/4.7.2"],
                FRAMEWORK: {
                    # Already past its branch fix, so nothing is remediated: this test is
                    # only about surviving shapes the manifest is not supposed to have.
                    "System.Drawing.Common/4.7.2": "this entry is a string, not an object",
                    "Other/1.0.0": {"dependencies": None},
                },
            },
            "libraries": {"System.Drawing.Common/4.7.2": "also not an object"},
        }, indent=2), encoding="utf-8")

        patch_upstream.remediate_app_dependencies(str(tmp_path))

        out = capsys.readouterr().out
        assert "Stage 1: Dynamic remediation check complete." in out
        assert "[REMEDIATE]" not in out
        assert deps_file.exists()


class TestAzureIdentityUpgrade:
    """Azure.Identity is the one package whose assemblyVersion moves with the fix."""

    def test_assembly_version_is_rewritten(self, tmp_path, monkeypatch):
        """1.3.0.0 -> 1.11.0.0 across every asset the entry declares."""
        stub_fetch(monkeypatch, payload=_pe_with_version((1 << 16) | 1100, (26 << 16) | 1))
        deps_file = write_deps(
            tmp_path,
            {"Azure.Identity/1.3.0": {
                "runtime": {"lib/netstandard2.0/Azure.Identity.dll":
                            {"assemblyVersion": "1.3.0.0", "fileVersion": "1.300.20.56202"}}}},
            {"Azure.Identity/1.3.0": {"sha512": "sha512-STALE=="}},
        )
        (tmp_path / "Azure.Identity.dll").write_bytes(b"old")

        patch_upstream.remediate_app_dependencies(str(tmp_path))

        entry = read_deps(deps_file)[0]["Azure.Identity/1.11.4"]
        asset = entry["runtime"]["lib/netstandard2.0/Azure.Identity.dll"]
        assert asset["assemblyVersion"] == "1.11.0.0", "assemblyVersion not moved to the 1.11 line"
        assert asset["fileVersion"] == "1.1100.26.1", "fileVersion not taken from the assembly"


class TestDependencyClosure:
    """Upgrading an assembly is useless if its dependencies stay behind."""

    def test_closure_is_installed_and_recorded(self, tmp_path, monkeypatch):
        """Closure members land next to the dependent and appear in its manifest."""
        spec = patch_upstream.TARGET_PACKAGES["Azure.Identity"]
        payloads = {}

        def fake_fetch(url, asset):
            payloads[url] = asset
            return b"MZ" + asset.encode()

        monkeypatch.setattr(patch_upstream, "fetch_nupkg_dll", fake_fetch)

        for app in ("Agent", "Server"):
            (tmp_path / app).mkdir()
            (tmp_path / app / "Azure.Identity.dll").write_bytes(b"old")
            write_deps(
                tmp_path / app,
                {"Azure.Identity/1.3.0": {"runtime": {"lib/netstandard2.0/Azure.Identity.dll": {}}}},
                {"Azure.Identity/1.3.0": {"sha512": "sha512-STALE=="}},
                name=f"{app}.deps.json",
            )

        patch_upstream.remediate_app_dependencies(str(tmp_path))

        assert len(payloads) == 1 + len(spec["closure"]), "not every closure member was fetched"
        for member in spec["closure"]:
            for app in ("Agent", "Server"):
                installed = tmp_path / app / f"{member['name']}.dll"
                assert installed.exists(), f"{member['name']} not placed next to Azure.Identity in {app}"

            targets, libraries = read_deps(tmp_path / "Server" / "Server.deps.json")
            key = f"{member['name']}/{member['version']}"
            assert key in targets, f"{key} missing from targets"
            assert key in libraries, f"{key} missing from libraries"
            assert member["asset"] in targets[key]["runtime"]
            assert libraries[key]["sha512"] == ""

    def test_closure_covers_azure_identity_requirements(self):
        """The recorded closure matches what Azure.Identity 1.11.4 actually needs."""
        closure = {m["name"]: m["version"] for m in patch_upstream.TARGET_PACKAGES["Azure.Identity"]["closure"]}
        # Resolved with `dotnet publish` for net10.0; see the comment on AZURE_IDENTITY_CLOSURE.
        assert closure == {
            "Azure.Core": "1.38.0",
            "Microsoft.Bcl.AsyncInterfaces": "1.1.1",
            "Microsoft.Identity.Client": "4.61.3",
            "Microsoft.Identity.Client.Extensions.Msal": "4.61.3",
            "System.ClientModel": "1.0.0",
            "System.Memory.Data": "1.0.2",
        }
        for member in patch_upstream.TARGET_PACKAGES["Azure.Identity"]["closure"]:
            assert member["asset"].endswith(f"/{member['name']}.dll"), f"{member['name']} asset path mismatch"

    def test_existing_closure_member_is_upgraded_in_place(self, tmp_path, monkeypatch):
        """A closure member already in the manifest is re-keyed, not duplicated."""
        monkeypatch.setattr(patch_upstream, "fetch_nupkg_dll", lambda url, asset: b"MZ" + asset.encode())
        (tmp_path / "Server").mkdir()
        for name in ("Azure.Identity.dll", "Azure.Core.dll"):
            (tmp_path / "Server" / name).write_bytes(b"old")
        deps_file = write_deps(
            tmp_path / "Server",
            {
                "Azure.Identity/1.3.0": {
                    "dependencies": {"Azure.Core": "1.6.0"},
                    "runtime": {"lib/netstandard2.0/Azure.Identity.dll": {}},
                },
                "Azure.Core/1.6.0": {
                    "runtime": {"lib/netstandard2.0/Azure.Core.dll": {"assemblyVersion": "1.6.0.0"}},
                },
            },
            {"Azure.Identity/1.3.0": {}, "Azure.Core/1.6.0": {"type": "package", "sha512": "sha512-OLD=="}},
            name="Server.deps.json",
        )

        patch_upstream.remediate_app_dependencies(str(tmp_path))

        targets, libraries = read_deps(deps_file)
        assert "Azure.Core/1.38.0" in targets and "Azure.Core/1.6.0" not in targets
        assert "Azure.Core/1.38.0" in libraries and "Azure.Core/1.6.0" not in libraries
        assert libraries["Azure.Core/1.38.0"]["sha512"] == "", "stale hash kept on an upgraded member"
        assert "lib/net6.0/Azure.Core.dll" in targets["Azure.Core/1.38.0"]["runtime"]
        # The dependency range on the dependent entry follows the member it points at.
        assert targets["Azure.Identity/1.11.4"]["dependencies"]["Azure.Core"] == "1.38.0"

    def test_only_manifests_referencing_the_package_are_touched(self, tmp_path, monkeypatch):
        """An unrelated manifest must not gain Azure dependencies it never had."""
        monkeypatch.setattr(patch_upstream, "fetch_nupkg_dll", lambda url, asset: b"MZ")
        (tmp_path / "App").mkdir()
        (tmp_path / "App" / "Azure.Identity.dll").write_bytes(b"old")
        write_deps(tmp_path / "App",
                   {"Azure.Identity/1.3.0": {"runtime": {"lib/netstandard2.0/Azure.Identity.dll": {}}}},
                   {"Azure.Identity/1.3.0": {}}, name="App.deps.json")
        (tmp_path / "Other").mkdir()
        unrelated = write_deps(tmp_path / "Other", {"Newtonsoft.Json/13.0.3": {}},
                               {"Newtonsoft.Json/13.0.3": {}}, name="Other.deps.json")
        before = unrelated.read_text(encoding="utf-8")

        patch_upstream.remediate_app_dependencies(str(tmp_path))

        assert unrelated.read_text(encoding="utf-8") == before, "unrelated manifest was modified"


class TestNativeAssetReplacement:
    """Native packages ship one binary per RID; each slot must get its own build."""

    @staticmethod
    def _package(entries):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, payload in entries.items():
                archive.writestr(name, payload)
        return buffer.getvalue()

    def _tree(self, tmp_path):
        for rid in ("linux-x64", "linux-arm64"):
            for app in ("Agent", "Server"):
                d = tmp_path / app / "runtimes" / rid / "native"
                d.mkdir(parents=True)
                (d / "libe_sqlite3.so").write_bytes(b"vulnerable-" + rid.encode())

    def test_each_rid_gets_its_own_build(self, tmp_path):
        """An x64 binary must never land in the arm64 slot."""
        self._tree(tmp_path)
        package = self._package({
            "runtimes/linux-x64/native/libe_sqlite3.so": b"fixed-x64",
            "runtimes/linux-arm64/native/libe_sqlite3.so": b"fixed-arm64",
            "runtimes/win-x64/native/e_sqlite3.dll": b"fixed-win",
        })

        count = patch_upstream.replace_rid_assets(str(tmp_path), package, "libe_sqlite3.so")

        assert count == 4, f"expected all four RID copies replaced, got {count}"
        for app in ("Agent", "Server"):
            base = tmp_path / app / "runtimes"
            assert (base / "linux-x64" / "native" / "libe_sqlite3.so").read_bytes() == b"fixed-x64"
            assert (base / "linux-arm64" / "native" / "libe_sqlite3.so").read_bytes() == b"fixed-arm64"

    def test_leaves_rids_the_package_does_not_ship(self, tmp_path):
        """A RID with no published asset is left alone rather than given a foreign build."""
        self._tree(tmp_path)
        package = self._package({"runtimes/linux-x64/native/libe_sqlite3.so": b"fixed-x64"})

        count = patch_upstream.replace_rid_assets(str(tmp_path), package, "libe_sqlite3.so")

        assert count == 2, "only the x64 slots should have been replaced"
        for app in ("Agent", "Server"):
            arm = tmp_path / app / "runtimes" / "linux-arm64" / "native" / "libe_sqlite3.so"
            assert arm.read_bytes() == b"vulnerable-linux-arm64", "arm64 slot was given a foreign build"

    def test_native_package_is_remediated_end_to_end(self, tmp_path, monkeypatch):
        """The native branch of the upgrade path re-keys the manifest and swaps binaries."""
        package = self._package({
            "runtimes/linux-x64/native/libe_sqlite3.so": b"fixed-x64",
            "runtimes/linux-arm64/native/libe_sqlite3.so": b"fixed-arm64",
        })
        monkeypatch.setattr(patch_upstream, "fetch_nupkg", lambda url: package)
        self._tree(tmp_path)
        deps_file = write_deps(
            tmp_path,
            {"SQLitePCLRaw.lib.e_sqlite3/2.1.11": {
                "runtimeTargets": {"runtimes/linux-x64/native/libe_sqlite3.so":
                                   {"rid": "linux-x64", "assetType": "native", "fileVersion": "0.0.0.0"}}}},
            {"SQLitePCLRaw.lib.e_sqlite3/2.1.11": {"sha512": "sha512-STALE=="}},
        )

        patch_upstream.remediate_app_dependencies(str(tmp_path))

        targets, libraries = read_deps(deps_file)
        assert "SQLitePCLRaw.lib.e_sqlite3/2.1.12" in targets
        assert "SQLitePCLRaw.lib.e_sqlite3/2.1.11" not in targets
        assert libraries["SQLitePCLRaw.lib.e_sqlite3/2.1.12"]["sha512"] == ""
        assert (tmp_path / "Agent" / "runtimes" / "linux-x64" / "native" / "libe_sqlite3.so").read_bytes() == b"fixed-x64"
        assert (tmp_path / "Server" / "runtimes" / "linux-arm64" / "native" / "libe_sqlite3.so").read_bytes() == b"fixed-arm64"

    def test_rejects_a_package_with_no_native_assets(self, tmp_path):
        """A package missing the expected assets fails loudly."""
        self._tree(tmp_path)
        with pytest.raises(RuntimeError, match="no runtimes"):
            patch_upstream.replace_rid_assets(str(tmp_path), self._package({"lib/net8.0/x.dll": b"x"}),
                                              "libe_sqlite3.so")


class TestNuGetFetch:
    """Assertions on download integrity checking."""

    @staticmethod
    def _nupkg(entries):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, payload in entries.items():
                archive.writestr(name, payload)
        return buffer.getvalue()

    def test_rejects_package_missing_the_requested_asset(self, monkeypatch):
        """A nupkg without the declared asset path must fail loudly, not return junk."""
        package = self._nupkg({"lib/net8.0/Other.dll": b"x"})
        monkeypatch.setattr(patch_upstream.urllib.request, "urlopen", _fake_urlopen(package))

        with pytest.raises(RuntimeError, match="is absent from"):
            patch_upstream.fetch_nupkg_dll("https://example.invalid/p.nupkg", "lib/net10.0/Wanted.dll")

    def test_rejects_empty_response_body(self, monkeypatch):
        """An empty HTTP body must not be silently treated as a valid package."""
        monkeypatch.setattr(patch_upstream.urllib.request, "urlopen", _fake_urlopen(b""))

        with pytest.raises(RuntimeError, match="empty response body"):
            patch_upstream.fetch_nupkg_dll("https://example.invalid/p.nupkg", "lib/net10.0/Wanted.dll")

    def test_rejects_non_200_response(self, monkeypatch):
        """An error status must not be parsed as a package."""
        monkeypatch.setattr(patch_upstream.urllib.request, "urlopen", _fake_urlopen(b"oops", status=503))
        with pytest.raises(RuntimeError, match="HTTP 503"):
            patch_upstream.fetch_nupkg_dll("https://example.invalid/p.nupkg", "lib/net10.0/Wanted.dll")

    def test_rejects_empty_asset(self, monkeypatch):
        """A zero-byte assembly inside a valid package is refused."""
        package = self._nupkg({"lib/net10.0/Wanted.dll": b""})
        monkeypatch.setattr(patch_upstream.urllib.request, "urlopen", _fake_urlopen(package))
        with pytest.raises(RuntimeError, match="is empty in"):
            patch_upstream.fetch_nupkg_dll("https://example.invalid/p.nupkg", "lib/net10.0/Wanted.dll")

    def test_returns_requested_asset_bytes(self, monkeypatch):
        """A well-formed package yields exactly the requested assembly."""
        package = self._nupkg({"lib/net10.0/Wanted.dll": FAKE_DLL})
        monkeypatch.setattr(patch_upstream.urllib.request, "urlopen", _fake_urlopen(package))

        result = patch_upstream.fetch_nupkg_dll("https://example.invalid/p.nupkg", "lib/net10.0/Wanted.dll")
        assert result == FAKE_DLL
        assert len(result) > 0


def _fake_urlopen(payload, status=200):
    """Build a urlopen replacement returning a fixed body as a context manager."""

    class _Response:
        def __init__(self):
            self.status = status

        def read(self):
            return payload

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    def _urlopen(_request, timeout=None):
        assert timeout is not None, "NuGet downloads must always specify a timeout"
        return _Response()

    return _urlopen
