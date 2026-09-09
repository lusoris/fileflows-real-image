"""Static analysis and architectural invariant verification for Dockerfile definitions."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = REPO_ROOT / "Dockerfile"
DOCKERFILE_OPTIMIZED = REPO_ROOT / "Dockerfile.optimized"


class TestDockerfileInvariants:
    """Static assertions ensuring Dockerfile definitions respect architectural directives."""

    def test_dockerfile_and_optimized_identical(self):
        """Invariant: Dockerfile and Dockerfile.optimized must remain 100% byte-identical."""
        assert DOCKERFILE.exists(), "Dockerfile must exist"
        assert DOCKERFILE_OPTIMIZED.exists(), "Dockerfile.optimized must exist"

        content_main = DOCKERFILE.read_text(encoding="utf-8")
        content_opt = DOCKERFILE_OPTIMIZED.read_text(encoding="utf-8")
        assert content_main == content_opt, "Drift detected between Dockerfile and Dockerfile.optimized!"

    def test_multi_stage_topology(self):
        """Invariant: Dockerfile must define all canonical multi-stage targets."""
        content = DOCKERFILE.read_text(encoding="utf-8")
        from_lines = re.findall(r"^FROM\s+([^\s]+)(?:\s+AS\s+([^\s]+))?", content, re.MULTILINE)

        stage_aliases = [alias for _, alias in from_lines if alias]
        expected_stages = [
            "upstream",
            "base-common",
            "base-intel",
            "base-amd",
            "base-cuda",
            "base-cuda13",
            "base-all",
            "base-selected",
            "base-flat",
        ]
        for stage in expected_stages:
            assert stage in stage_aliases, f"Expected stage '{stage}' missing from Dockerfile stage topology."

    def test_rootfs_squashing_and_pebble_purge(self):
        """Invariant: Layer flattening via FROM scratch COPY --from=base-selected must be preserved."""
        content = DOCKERFILE.read_text(encoding="utf-8")
        assert "FROM scratch AS base-flat" in content, "Rootfs flattening stage 'FROM scratch AS base-flat' missing."
        assert re.search(r"COPY\s+--from=base-selected\s+/\s+/", content), (
            "Squashing copy 'COPY --from=base-selected / /' missing."
        )

        # Pebble purge rm command
        assert re.search(r"rm\s+-rf\s+.*pebble", content), "Pebble daemon cleanup instruction missing from Dockerfile."

    def test_no_dotnet_sdk_installed(self):
        """Invariant: Never install dotnet-sdk-*; only aspnetcore-runtime-10.0."""
        content = DOCKERFILE.read_text(encoding="utf-8")
        assert "dotnet-sdk" not in content, "Forbidden package 'dotnet-sdk' referenced in Dockerfile."
        assert "aspnetcore-runtime-10.0" in content, "Production runtime 'aspnetcore-runtime-10.0' must be installed."

    def test_no_development_packages(self):
        """Invariant: Production stages must not install -dev header packages."""
        content = DOCKERFILE.read_text(encoding="utf-8")
        # Match any package ending in -dev followed by space or newline in apt-get install commands
        dev_matches = re.findall(r"apt-get\s+install[^;]+?([a-zA-Z0-9_-]+-dev)", content, re.DOTALL)
        assert len(dev_matches) == 0, f"Found forbidden -dev package(s) in apt-get install: {dev_matches}"

    def test_cuda_flavor_architectures(self):
        """Invariant: :cuda must be host-based driver injection; :cuda13 must install only video filter essentials."""
        content = DOCKERFILE.read_text(encoding="utf-8")

        # base-cuda stage must just inherit base-common with no package installations
        cuda_stage_match = re.search(
            r"FROM\s+base-common\s+AS\s+base-cuda\n(.*?)(?=FROM\s+base-common\s+AS\s+base-cuda13)",
            content,
            re.DOTALL,
        )
        assert cuda_stage_match, "base-cuda stage definition not found."
        cuda_stage_body = cuda_stage_match.group(1)
        assert "apt-get" not in cuda_stage_body, "base-cuda must not install any apt packages (host driver injection)."

        # base-cuda13 stage must install only nvrtc, cudart, and npp
        cuda13_stage_match = re.search(
            r"FROM\s+base-common\s+AS\s+base-cuda13\n(.*?)(?=FROM\s+base-common\s+AS\s+base-all)",
            content,
            re.DOTALL,
        )
        assert cuda13_stage_match, "base-cuda13 stage definition not found."
        cuda13_body = cuda13_stage_match.group(1)
        assert "cuda-nvrtc-13-4" in cuda13_body
        assert "cuda-cudart-13-4" in cuda13_body
        assert "libnpp-13-4" in cuda13_body

        # Disallowed bloated CUDA compute packages
        for heavy_pkg in ["libcublas", "libcusolver", "libcusparse", "libcufft", "cuda-compat"]:
            assert heavy_pkg not in content, f"Forbidden heavy CUDA package '{heavy_pkg}' found in Dockerfile."

    def test_runtime_apt_neutralization(self):
        """Invariant: entrypoint script apt-get calls must be neutralized via sed."""
        content = DOCKERFILE.read_text(encoding="utf-8")
        assert "sed -i" in content, "sed command neutralizing startup apt-get calls missing."
        assert "Hardware acceleration pre-configured" in content, (
            "Entrypoint echo log indicator missing from Dockerfile sed replacement."
        )

    def test_environment_and_healthcheck(self):
        """Invariant: Environment variables and native HEALTHCHECK must be defined."""
        content = DOCKERFILE.read_text(encoding="utf-8")
        assert "NVIDIA_VISIBLE_DEVICES=all" in content
        assert "NVIDIA_DRIVER_CAPABILITIES=compute,video,utility" in content
        assert "DOTNET_CLI_TELEMETRY_OPTOUT=1" in content
        assert "DOTNET_EnableDiagnostics=0" in content
        assert "HEALTHCHECK" in content
        assert "ENTRYPOINT" in content
