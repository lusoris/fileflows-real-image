"""Image content size measurement utility for FileFlows Real Image.

Queries upstream and published GHCR container image manifests via Docker Buildx
to measure exact layer content sizes, decimal megabytes, and reduction ratios.
Adheres strictly to NASA/JPL Power of 10 rules: short functions (<= 60 lines),
bounded iterations, and no dynamic evaluation.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

FLAVOR_DEFINITIONS: list[tuple[str, str, str]] = [
    ("latest", "Universal Default", "all | intel | amd | cuda | cuda13"),
    ("intel", "Intel QuickSync & Arc", "intel"),
    ("amd", "AMD Radeon & APU", "amd"),
    ("cuda", "NVIDIA Host CUDA", "cuda"),
    ("cuda13", "NVIDIA CUDA 13.4", "cuda13"),
]

DEFAULT_UPSTREAM_IMAGE = "revenz/fileflows:latest"
DEFAULT_REPO_PREFIX = "ghcr.io/lusoris/fileflows-real-image"
FALLBACK_UPSTREAM_BYTES = 811_717_760  # 812 MB


def bytes_to_decimal_mb(num_bytes: int) -> int:
    """Convert bytes to decimal megabytes (MB, 10^6) with standard rounding."""
    if num_bytes <= 0:
        return 0
    return (num_bytes + 500_000) // 1_000_000


def compute_reduction(upstream_mb: int, flavor_mb: int) -> tuple[int, float]:
    """Compute difference in MB and percentage reduction relative to upstream."""
    if upstream_mb <= 0:
        return 0, 0.0
    diff_mb = upstream_mb - flavor_mb
    pct = round((diff_mb / upstream_mb) * 100.0, 1)
    return diff_mb, pct


def extract_layer_bytes_from_manifest(manifest_data: dict[str, Any]) -> int:
    """Extract and sum layer sizes from an OCI or Docker image manifest."""
    layers = manifest_data.get("layers", [])
    if not isinstance(layers, list):
        return 0
    total = 0
    for layer in layers:
        if isinstance(layer, dict):
            size = layer.get("size", 0)
            if isinstance(size, int) and size > 0:
                total += size
    return total


def inspect_raw_manifest(image_ref: str) -> dict[str, Any] | None:
    """Query buildx imagetools inspect --raw for an image reference."""
    cmd = ["docker", "buildx", "imagetools", "inspect", "--raw", image_ref]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        return json.loads(proc.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return None


def measure_image_bytes(image_ref: str, target_arch: str = "amd64") -> int:
    """Resolve and sum layer sizes for the target architecture from an image reference."""
    data = inspect_raw_manifest(image_ref)
    if not data:
        return 0

    # If it is a multi-arch manifest list / index, resolve child digest for target_arch
    if "manifests" in data and isinstance(data["manifests"], list):
        base_repo = image_ref.split(":")[0].split("@")[0]
        for m in data["manifests"]:
            if not isinstance(m, dict):
                continue
            platform = m.get("platform", {})
            if platform.get("architecture") == target_arch and platform.get("os") == "linux":
                digest = m.get("digest")
                if digest:
                    child_data = inspect_raw_manifest(f"{base_repo}@{digest}")
                    if child_data:
                        return extract_layer_bytes_from_manifest(child_data)

    return extract_layer_bytes_from_manifest(data)


def measure_all_metrics(
    repo_prefix: str = DEFAULT_REPO_PREFIX,
    upstream_ref: str = DEFAULT_UPSTREAM_IMAGE,
    target_arch: str = "amd64",
) -> dict[str, Any]:
    """Gather complete size and reduction metrics for upstream and all image flavors."""
    upstream_bytes = measure_image_bytes(upstream_ref, target_arch)
    if upstream_bytes == 0:
        upstream_bytes = FALLBACK_UPSTREAM_BYTES
    upstream_mb = bytes_to_decimal_mb(upstream_bytes)

    flavor_results: dict[str, Any] = {}
    for tag, display_name, _ in FLAVOR_DEFINITIONS:
        image_ref = f"{repo_prefix}:{tag}"
        f_bytes = measure_image_bytes(image_ref, target_arch)
        f_mb = bytes_to_decimal_mb(f_bytes)
        diff_mb, pct = compute_reduction(upstream_mb, f_mb) if f_mb > 0 else (0, 0.0)

        flavor_results[tag] = {
            "tag": tag,
            "display_name": display_name,
            "bytes": f_bytes,
            "size_mb": f_mb,
            "diff_mb": diff_mb,
            "reduction_pct": pct,
        }

    return {
        "upstream_ref": upstream_ref,
        "upstream_bytes": upstream_bytes,
        "upstream_mb": upstream_mb,
        "target_arch": target_arch,
        "flavors": flavor_results,
    }


def format_markdown_table(metrics: dict[str, Any]) -> str:
    """Format measured metrics into a GitHub-flavored Markdown table."""
    upstream_mb = metrics.get("upstream_mb", 0)
    flavors = metrics.get("flavors", {})

    lines = [
        "| Flavor | Tag | Content Size | Upstream Baseline | Reduction |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    for tag, display_name, _ in FLAVOR_DEFINITIONS:
        f_data = flavors.get(tag, {})
        f_mb = f_data.get("size_mb", 0)
        pct = f_data.get("reduction_pct", 0.0)
        diff_mb = f_data.get("diff_mb", 0)

        tag_col = f"`:{tag}`"
        if tag == "latest":
            tag_col = "`:all` / `:latest`"

        size_display = f"{f_mb} MB" if f_mb > 0 else "unmeasured"
        reduction_display = f"**-{pct}%** (-{diff_mb} MB)" if f_mb > 0 else "N/A"

        lines.append(
            f"| **{display_name}** | {tag_col} | {size_display} | {upstream_mb} MB | {reduction_display} |"
        )

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for measuring and reporting image sizes."""
    parser = argparse.ArgumentParser(description="Measure FileFlows Real Image sizes")
    parser.add_argument("--repo-prefix", default=DEFAULT_REPO_PREFIX, help="GHCR repository prefix")
    parser.add_argument("--upstream", default=DEFAULT_UPSTREAM_IMAGE, help="Upstream image reference")
    parser.add_argument("--arch", default="amd64", help="Target architecture (default: amd64)")
    parser.add_argument("--markdown", action="store_true", help="Output Markdown table only")
    parser.add_argument("--json", action="store_true", help="Output JSON metrics only")

    args = parser.parse_args(argv)
    metrics = measure_all_metrics(args.repo_prefix, args.upstream, args.arch)

    if args.json:
        print(json.dumps(metrics, indent=2))
        return 0

    if args.markdown:
        print(format_markdown_table(metrics))
        return 0

    # Default output: print both summary and Markdown table
    print(f"Upstream ({metrics['upstream_ref']}): {metrics['upstream_mb']} MB ({metrics['upstream_bytes']} bytes)")
    print("\nFlavor Matrix:")
    print(format_markdown_table(metrics))
    return 0


if __name__ == "__main__":
    sys.exit(main())
