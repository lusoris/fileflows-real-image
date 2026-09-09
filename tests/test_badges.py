"""Test suite validating dynamic Shields.io badge endpoint schemas and metric integrity."""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BADGES_DIR = REPO_ROOT / "docs" / "badges"
VERSION_FILE = REPO_ROOT / "version.txt"


class TestShieldsBadges:
    """Assertions ensuring dynamic badge JSON endpoints conform to Shields.io specifications."""

    def test_badge_files_exist_and_valid_schema(self):
        """Assert every badge file in docs/badges conforms to Shields.io schema."""
        assert BADGES_DIR.is_dir(), "docs/badges directory must exist"
        badge_files = list(BADGES_DIR.glob("*.json"))
        assert len(badge_files) >= 3, f"Expected at least 3 badge JSON files, found {len(badge_files)}"

        for bf in badge_files:
            data = json.loads(bf.read_text(encoding="utf-8"))
            assert data.get("schemaVersion") == 1, f"{bf.name} must specify schemaVersion: 1"
            assert "label" in data, f"{bf.name} missing 'label'"
            assert "message" in data, f"{bf.name} missing 'message'"
            assert "color" in data, f"{bf.name} missing 'color'"
            assert len(str(data["message"]).strip()) > 0, f"{bf.name} message must not be empty"

    def test_upstream_version_badge_matches_version_txt(self):
        """Assert docs/badges/upstream-version.json matches version.txt content."""
        version_badge = BADGES_DIR / "upstream-version.json"
        assert version_badge.exists()
        badge_data = json.loads(version_badge.read_text(encoding="utf-8"))
        pinned_version = VERSION_FILE.read_text(encoding="utf-8").strip()
        assert badge_data["message"] == pinned_version, (
            f"Upstream badge version '{badge_data['message']}' does not match version.txt '{pinned_version}'"
        )

    def test_flavors_badge_contains_all_hardware_targets(self):
        """Assert docs/badges/flavors.json includes all 5 hardware flavors."""
        flavors_badge = BADGES_DIR / "flavors.json"
        assert flavors_badge.exists()
        badge_data = json.loads(flavors_badge.read_text(encoding="utf-8"))
        msg = badge_data["message"]
        for expected in ["all", "intel", "amd", "cuda", "cuda13"]:
            assert expected in msg, f"Flavor '{expected}' missing from flavors badge message: {msg}"
