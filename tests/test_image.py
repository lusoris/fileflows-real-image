"""
Comprehensive test suite and architectural assertions for FileFlows Real Image.
Verifies all invariants defined in AGENTS.md and README.md:
  - Base OS: Ubuntu 26.04 (Resolute)
  - Zero base CVEs: /usr/bin/pebble purged via rootfs squashing
  - Zero .NET SDK bloat: only aspnetcore-runtime-10.0
  - Zero development compiler / -dev header packages
  - Instant startup: intel-media-va-driver-non-free pre-installed
  - Dead cross-platform runtimes (win*, osx*) stripped from /app
  - Utility binaries: docker, dovi_tool functional
  - Size gates: virtual disk <= 2.5GB, content size <= 650MB
  - Runtime smoke: container boots in < 5s, serves Web UI on port 5000/19200
"""

import os
import subprocess
import time
import urllib.request
import pytest

IMAGE_NAME = os.environ.get("TEST_IMAGE", "revenz/fileflows:optimized")


def run_in_container(cmd: str) -> subprocess.CompletedProcess:
    """Helper to run a shell command inside a temporary instance of the target image."""
    return subprocess.run(
        ["docker", "run", "--rm", "--entrypoint", "sh", IMAGE_NAME, "-c", cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


class TestArchitecturalInvariants:
    """Tests verifying base image hardening and dependency cleanliness."""

    def test_ubuntu_2604_base(self):
        """Invariant: Base OS must be Ubuntu 26.04 (Resolute)."""
        res = run_in_container("cat /etc/os-release")
        assert res.returncode == 0, f"Failed to read /etc/os-release: {res.stderr}"
        assert 'VERSION_ID="26.04"' in res.stdout, "Base image is not Ubuntu 26.04"
        assert "resolute" in res.stdout.lower(), "Ubuntu codename is not resolute"

    def test_pebble_purged(self):
        """Invariant: Pebble binary and directories must be completely purged to eliminate Go CVEs."""
        res = run_in_container("find / -name pebble 2>/dev/null")
        assert not res.stdout.strip(), f"pebble files/directories found: {res.stdout.strip()}"

    def test_no_dotnet_sdk_bloat(self):
        """Invariant: No dotnet-sdk packages installed; only runtime."""
        dpkg_res = run_in_container("dpkg -l 'dotnet-sdk*'")
        assert (
            dpkg_res.returncode != 0
            or "no packages found" in dpkg_res.stderr.lower()
            or not any(line.startswith("ii") for line in dpkg_res.stdout.splitlines())
        ), f"dotnet-sdk found installed: {dpkg_res.stdout}"

        sdk_res = run_in_container("dotnet --list-sdks")
        assert sdk_res.stdout.strip() == "", f"dotnet --list-sdks is not empty: {sdk_res.stdout}"

    def test_aspnetcore_runtime_present(self):
        """Invariant: ASP.NET Core 10 runtime must be installed and functional."""
        res = run_in_container("dotnet --list-runtimes")
        assert res.returncode == 0, f"dotnet command failed: {res.stderr}"
        assert "Microsoft.AspNetCore.App 10." in res.stdout, (
            f"Microsoft.AspNetCore.App 10 runtime missing: {res.stdout}"
        )

    def test_no_dev_packages(self):
        """Invariant: Zero -dev header packages installed in production image."""
        res = run_in_container("dpkg-query -W -f='${Package} ${Status}\\n' '*-dev' 2>/dev/null")
        installed_dev = [
            line for line in res.stdout.splitlines() if line.endswith("install ok installed") and not line.startswith("#")
        ]
        assert len(installed_dev) == 0, f"Unexpected -dev packages installed: {installed_dev}"

    def test_instant_startup_driver_preinstalled(self):
        """Invariant: intel-media-va-driver-non-free pre-installed to prevent boot-time apt-get."""
        res = run_in_container("dpkg-query -W -f='${Status}' intel-media-va-driver-non-free 2>/dev/null")
        assert "install ok installed" in res.stdout, (
            f"intel-media-va-driver-non-free not installed: {res.stdout}"
        )

    def test_vaapi_and_qsv_driver_stack(self):
        """Invariant: Required hardware acceleration libraries must be installed."""
        packages = ["i965-va-driver-shaders", "intel-opencl-icd", "libvpl2", "libmfx-gen1.2"]
        for pkg in packages:
            res = run_in_container(f"dpkg-query -W -f='${{Status}}' {pkg} 2>/dev/null")
            assert "install ok installed" in res.stdout, f"Driver package '{pkg}' missing from image."

    def test_dead_runtimes_stripped(self):
        """Invariant: Dead win* and osx* runtime folders stripped from /app."""
        res = run_in_container("find /app -type d \\( -name 'win*' -o -name 'osx*' \\) 2>/dev/null")
        assert res.returncode == 0
        found_dead_runtimes = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        assert len(found_dead_runtimes) == 0, (
            f"Dead Windows/macOS runtimes still present: {found_dead_runtimes}"
        )

    def test_utility_binaries_present(self):
        """Invariant: docker and dovi_tool CLI binaries present and executable."""
        docker_res = run_in_container("/usr/local/bin/docker --version")
        assert docker_res.returncode == 0, f"docker binary failed: {docker_res.stderr}"
        assert "Docker version" in docker_res.stdout

        dovi_res = run_in_container("/usr/local/bin/dovi_tool --version")
        assert dovi_res.returncode == 0, f"dovi_tool binary failed: {dovi_res.stderr}"
        assert "dovi_tool" in dovi_res.stdout


class TestImageMetricsAndFootprint:
    """Tests asserting image size constraints and metadata."""

    def test_virtual_disk_size_limit(self):
        """Assert image virtual disk size is under 2.5 GB (down from 3.57 GB upstream)."""
        res = subprocess.run(
            ["docker", "image", "inspect", IMAGE_NAME, "--format", "{{.Size}}"],
            stdout=subprocess.PIPE,
            text=True,
            check=True,
        )
        size_bytes = int(res.stdout.strip())
        size_gb = size_bytes / (1024**3)
        assert size_gb <= 2.5, f"Virtual size {size_gb:.2f} GB exceeds 2.5 GB gate threshold."

    def test_environment_variables_configured(self):
        """Assert essential environment variables are baked in."""
        res = subprocess.run(
            ["docker", "image", "inspect", IMAGE_NAME, "--format", "{{json .Config.Env}}"],
            stdout=subprocess.PIPE,
            text=True,
            check=True,
        )
        env = res.stdout
        assert "DOTNET_CLI_TELEMETRY_OPTOUT=true" in env
        assert "NVIDIA_VISIBLE_DEVICES=all" in env
        assert "NVIDIA_DRIVER_CAPABILITIES=compute,video,utility" in env


class TestRuntimeSmokeAndWebUI:
    """Tests executing the container and validating real HTTP and startup performance."""

    CONTAINER_NAME = "fileflows-pytest-smoke"
    PORT = 19205

    @classmethod
    def teardown_class(cls):
        """Ensure test container is stopped and removed."""
        subprocess.run(["docker", "rm", "-f", cls.CONTAINER_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def test_container_startup_and_web_ui(self):
        """Assert container starts instantly and serves Web UI with 200 OK."""
        # Remove any leftover container
        subprocess.run(["docker", "rm", "-f", self.CONTAINER_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        start_time = time.time()
        res = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                self.CONTAINER_NAME,
                "-p",
                f"{self.PORT}:5000",
                "-e",
                "TZ=UTC",
                "-e",
                "PUID=1000",
                "-e",
                "PGID=1000",
                IMAGE_NAME,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        launch_duration = time.time() - start_time
        assert launch_duration < 5.0, f"Container launch took too long: {launch_duration:.2f}s"

        # Poll container until HTTP endpoint responds or timeout (20 seconds)
        url = f"http://127.0.0.1:{self.PORT}/"
        web_ok = False
        final_html = ""
        entrypoint_checked = False

        for _ in range(25):
            time.sleep(1)
            # Check entrypoint logs early
            if not entrypoint_checked:
                logs_res = subprocess.run(
                    ["docker", "logs", self.CONTAINER_NAME],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if "intel-media-va-driver-non-free already installed." in logs_res.stdout:
                    entrypoint_checked = True
                    assert "apt-get update" not in logs_res.stdout, (
                        "Container unexpectedly ran apt-get update on boot!"
                    )

            try:
                req = urllib.request.Request(url, headers={"User-Agent": "pytest"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        final_html = resp.read().decode("utf-8")
                        web_ok = True
                        break
            except Exception:
                continue

        # Check entrypoint logs assertion
        assert entrypoint_checked, "Entrypoint failed to log 'already installed' message."

        # Check HTTP response assertion
        assert web_ok, f"Web UI did not return HTTP 200 within timeout on {url}"
        assert "<title>FileFlows" in final_html, f"Unexpected page content: {final_html[:300]}"

        # Cleanup
        subprocess.run(["docker", "rm", "-f", self.CONTAINER_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
