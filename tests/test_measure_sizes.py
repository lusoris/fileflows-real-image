"""Unit test suite for scripts/measure_sizes.py validating sizing logic and table output."""

import json
from pathlib import Path
import sys
from unittest.mock import patch
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from measure_sizes import (
    bytes_to_decimal_mb,
    compute_reduction,
    extract_layer_bytes_from_manifest,
    format_markdown_table,
    main,
    measure_all_metrics,
)


class TestMeasureSizes:
    """Test suite validating image measurement, math, and reporting utilities."""

    def test_bytes_to_decimal_mb(self):
        """Assert conversion to decimal MB correctly rounds according to standard math."""
        assert bytes_to_decimal_mb(811_717_760) == 812
        assert bytes_to_decimal_mb(574_358_413) == 574
        assert bytes_to_decimal_mb(514_786_695) == 515
        assert bytes_to_decimal_mb(473_072_283) == 473
        assert bytes_to_decimal_mb(387_071_301) == 387
        assert bytes_to_decimal_mb(702_885_257) == 703
        assert bytes_to_decimal_mb(0) == 0
        assert bytes_to_decimal_mb(-100) == 0

    def test_compute_reduction(self):
        """Assert difference and percentage reduction calculations are accurate."""
        diff, pct = compute_reduction(812, 574)
        assert diff == 238
        assert pct == 29.3

        diff_intel, pct_intel = compute_reduction(812, 515)
        assert diff_intel == 297
        assert pct_intel == 36.6

        diff_cuda, pct_cuda = compute_reduction(812, 387)
        assert diff_cuda == 425
        assert pct_cuda == 52.3

        diff_zero, pct_zero = compute_reduction(0, 500)
        assert diff_zero == 0
        assert pct_zero == 0.0

    def test_extract_layer_bytes_from_manifest(self):
        """Assert layer sizes are extracted safely from manifest dictionaries."""
        manifest = {
            "schemaVersion": 2,
            "layers": [
                {"mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip", "size": 100_000_000},
                {"mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip", "size": 250_000_000},
            ],
        }
        assert extract_layer_bytes_from_manifest(manifest) == 350_000_000

        empty_manifest = {}
        assert extract_layer_bytes_from_manifest(empty_manifest) == 0

        invalid_layers = {"layers": "not-a-list"}
        assert extract_layer_bytes_from_manifest(invalid_layers) == 0

    def test_format_markdown_table(self):
        """Assert Markdown table format contains required headers and all flavors."""
        sample_metrics = {
            "upstream_mb": 812,
            "flavors": {
                "latest": {"size_mb": 574, "reduction_pct": 29.3, "diff_mb": 238},
                "intel": {"size_mb": 515, "reduction_pct": 36.6, "diff_mb": 297},
                "amd": {"size_mb": 473, "reduction_pct": 41.7, "diff_mb": 339},
                "cuda": {"size_mb": 387, "reduction_pct": 52.3, "diff_mb": 425},
                "cuda13": {"size_mb": 703, "reduction_pct": 13.4, "diff_mb": 109},
            },
        }
        table = format_markdown_table(sample_metrics)
        assert "| Flavor | Tag | Content Size | Upstream Baseline | Reduction |" in table
        assert "| **Universal Default** | `:all` / `:latest` | 574 MB | 812 MB | **-29.3%** (-238 MB) |" in table
        assert "| **Intel QuickSync & Arc** | `:intel` | 515 MB | 812 MB | **-36.6%** (-297 MB) |" in table
        assert "| **AMD Radeon & APU** | `:amd` | 473 MB | 812 MB | **-41.7%** (-339 MB) |" in table
        assert "| **NVIDIA Host CUDA** | `:cuda` | 387 MB | 812 MB | **-52.3%** (-425 MB) |" in table
        assert "| **NVIDIA CUDA 13.4** | `:cuda13` | 703 MB | 812 MB | **-13.4%** (-109 MB) |" in table

    def test_measure_all_metrics_with_mock(self):
        """Assert measure_all_metrics constructs expected schema with mock resolution."""
        with patch("measure_sizes.measure_image_bytes") as mock_measure:
            mock_measure.side_effect = lambda ref, arch: 812_000_000 if "revenz" in ref else 500_000_000
            metrics = measure_all_metrics()
            assert metrics["upstream_mb"] == 812
            assert "latest" in metrics["flavors"]
            assert metrics["flavors"]["latest"]["size_mb"] == 500
            assert metrics["flavors"]["latest"]["diff_mb"] == 312

    def test_cli_flags(self, capsys):
        """Assert CLI invocation handles --json and --markdown flags properly."""
        sample_metrics = {
            "upstream_ref": "revenz/fileflows:latest",
            "upstream_bytes": 812_000_000,
            "upstream_mb": 812,
            "target_arch": "amd64",
            "flavors": {
                "latest": {
                    "tag": "latest",
                    "display_name": "Universal Default",
                    "bytes": 574_000_000,
                    "size_mb": 574,
                    "diff_mb": 238,
                    "reduction_pct": 29.3,
                }
            },
        }
        with patch("measure_sizes.measure_all_metrics", return_value=sample_metrics):
            rc_json = main(["--json"])
            captured_json = capsys.readouterr().out
            assert rc_json == 0
            parsed = json.loads(captured_json)
            assert parsed["upstream_mb"] == 812

            rc_md = main(["--markdown"])
            captured_md = capsys.readouterr().out
            assert rc_md == 0
            assert "| Flavor | Tag |" in captured_md

            rc_default = main([])
            captured_default = capsys.readouterr().out
            assert rc_default == 0
            assert "Upstream (revenz/fileflows:latest):" in captured_default

    def test_inspect_raw_manifest_branches(self):
        """Assert inspect_raw_manifest handles success, subprocess failure, and parse errors."""
        from measure_sizes import inspect_raw_manifest
        from unittest.mock import MagicMock

        # Success case
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='{"schemaVersion": 2}')
            res = inspect_raw_manifest("test:tag")
            assert res == {"schemaVersion": 2}

            # Non-zero returncode
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            assert inspect_raw_manifest("test:tag") is None

            # Invalid JSON
            mock_run.return_value = MagicMock(returncode=0, stdout="not-json")
            assert inspect_raw_manifest("test:tag") is None

            # Exception
            mock_run.side_effect = OSError("command not found")
            assert inspect_raw_manifest("test:tag") is None

    def test_measure_image_bytes_multiarch_and_single(self):
        """Assert measure_image_bytes resolves multiarch manifest and single manifest."""
        from measure_sizes import measure_image_bytes

        # Multiarch manifest
        multiarch = {
            "manifests": [
                {
                    "platform": {"architecture": "amd64", "os": "linux"},
                    "digest": "sha256:child_amd64",
                },
                {
                    "platform": {"architecture": "arm64", "os": "linux"},
                    "digest": "sha256:child_arm64",
                },
            ]
        }
        child_manifest = {
            "layers": [
                {"size": 120_000_000},
                {"size": 80_000_000},
            ]
        }

        def mock_inspect(ref):
            if "child_amd64" in ref:
                return child_manifest
            if "parent" in ref:
                return multiarch
            return None

        with patch("measure_sizes.inspect_raw_manifest", side_effect=mock_inspect):
            size = measure_image_bytes("ghcr.io/repo:parent", "amd64")
            assert size == 200_000_000

            size_missing = measure_image_bytes("ghcr.io/repo:nonexistent", "amd64")
            assert size_missing == 0

    def test_measure_all_metrics_upstream_fallback(self):
        """Assert measure_all_metrics uses fallback bytes when upstream fails inspection."""
        with patch("measure_sizes.measure_image_bytes", return_value=0):
            metrics = measure_all_metrics()
            assert metrics["upstream_bytes"] == 811_717_760
            assert metrics["upstream_mb"] == 812
