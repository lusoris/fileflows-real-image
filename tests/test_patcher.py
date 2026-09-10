"""
Unit tests for the dynamic semantic NuGet vulnerability remediator.
Verifies idempotent behavior, absence of downgrades, and clean skipping.
"""

import json
from pathlib import Path
import pytest
import sys

# Add scripts directory to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import patch_upstream  # noqa: E402


class TestPatchUpstream:
    def test_parse_version(self):
        """Verify semantic version string parsing."""
        assert patch_upstream.parse_version("1.21.0") == (1, 21, 0)
        assert patch_upstream.parse_version("1.22.0") == (1, 22, 0)
        assert patch_upstream.parse_version("5.2.2") == (5, 2, 2)
        assert patch_upstream.parse_version("5.202.24263.2") == (5, 202, 24263, 2)
        assert patch_upstream.parse_version("8.0.0-preview.1") == (8, 0, 0)
        assert patch_upstream.parse_version("unknown") == (0,)

    def test_version_comparisons(self):
        """Verify version comparison thresholds match security policies."""
        # Azure.Identity: >= 1.21.0
        assert patch_upstream.parse_version("1.3.0") < (1, 21, 0)
        assert patch_upstream.parse_version("1.20.0") < (1, 21, 0)
        assert patch_upstream.parse_version("1.21.0") >= (1, 21, 0)
        assert patch_upstream.parse_version("1.22.0") >= (1, 21, 0)

        # Microsoft.Data.SqlClient: >= 5.2.2
        assert patch_upstream.parse_version("3.0.0") < (5, 2, 2)
        assert patch_upstream.parse_version("5.2.1") < (5, 2, 2)
        assert patch_upstream.parse_version("5.2.2") >= (5, 2, 2)
        assert patch_upstream.parse_version("6.0.0") >= (5, 2, 2)

        # System.Drawing.Common: >= 8.0.0
        assert patch_upstream.parse_version("4.7.0") < (8, 0, 0)
        assert patch_upstream.parse_version("7.0.0") < (8, 0, 0)
        assert patch_upstream.parse_version("8.0.0") >= (8, 0, 0)
        assert patch_upstream.parse_version("9.0.0") >= (8, 0, 0)

    def test_skips_when_upstream_already_clean(self, tmp_path, capsys):
        """Verify remediator does not downgrade or modify clean upstream dependencies."""
        mock_deps = {
            "runtimeTarget": {"name": ".NETCoreApp,Version=v10.0"},
            "targets": {
                ".NETCoreApp,Version=v10.0": {
                    "Azure.Identity/1.22.0": {
                        "runtime": {"lib/net10.0/Azure.Identity.dll": {}}
                    },
                    "Microsoft.Data.SqlClient/5.3.0": {
                        "runtimeTargets": {"runtimes/unix/lib/net8.0/Microsoft.Data.SqlClient.dll": {}}
                    },
                    "System.Drawing.Common/8.0.1": {
                        "runtime": {"lib/netstandard2.0/System.Drawing.Common.dll": {}}
                    },
                }
            },
            "libraries": {
                "Azure.Identity/1.22.0": {},
                "Microsoft.Data.SqlClient/5.3.0": {},
                "System.Drawing.Common/8.0.1": {},
            },
        }

        deps_file = tmp_path / "App.deps.json"
        deps_file.write_text(json.dumps(mock_deps, indent=2), encoding="utf-8")

        # Run remediation against mock clean directory
        patch_upstream.remediate_app_dependencies(str(tmp_path))

        captured = capsys.readouterr().out
        assert "[UPSTREAM CLEAN] Azure.Identity" in captured
        assert "[UPSTREAM CLEAN] Microsoft.Data.SqlClient" in captured
        assert "[UPSTREAM CLEAN] System.Drawing.Common" in captured
        assert "No patch needed" in captured

        # Verify no downgrade occurred in .deps.json
        updated = json.loads(deps_file.read_text(encoding="utf-8"))
        targets = updated["targets"][".NETCoreApp,Version=v10.0"]
        assert "Azure.Identity/1.22.0" in targets
        assert "Microsoft.Data.SqlClient/5.3.0" in targets
        assert "System.Drawing.Common/8.0.1" in targets

    def test_skips_when_packages_not_present(self, tmp_path, capsys):
        """Verify remediator cleanly skips packages absent in upstream dependencies."""
        mock_deps = {
            "runtimeTarget": {"name": ".NETCoreApp,Version=v10.0"},
            "targets": {
                ".NETCoreApp,Version=v10.0": {
                    "Newtonsoft.Json/13.0.3": {}
                }
            },
            "libraries": {
                "Newtonsoft.Json/13.0.3": {}
            },
        }

        deps_file = tmp_path / "App.deps.json"
        deps_file.write_text(json.dumps(mock_deps, indent=2), encoding="utf-8")

        patch_upstream.remediate_app_dependencies(str(tmp_path))

        captured = capsys.readouterr().out
        assert "[UPSTREAM CLEAN] Azure.Identity: Not present in upstream dependencies. Skipped." in captured
        assert "[UPSTREAM CLEAN] Microsoft.Data.SqlClient: Not present in upstream dependencies. Skipped." in captured
        assert "[UPSTREAM CLEAN] System.Drawing.Common: Not present in upstream dependencies. Skipped." in captured
