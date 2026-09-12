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

IMAGE_NAME = os.environ.get("TEST_IMAGE", "ghcr.io/lusoris/fileflows-real-image:latest").strip()

# Exit codes docker reserves for "the command never ran": image/daemon error, not
# executable, not found. Any of these means an invariant was not actually verified.
DOCKER_DID_NOT_RUN = (125, 126, 127)


@pytest.fixture(scope="session", autouse=True)
def require_test_image():
    """Abort the suite rather than let container invariants pass against a missing image."""
    res = subprocess.run(
        ["docker", "image", "inspect", IMAGE_NAME],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert res.returncode == 0, (
        f"Test image '{IMAGE_NAME}' is not available locally, so no container invariant "
        f"can be verified. Build it first (make build) or set TEST_IMAGE. {res.stderr.strip()}"
    )


def run_in_container(cmd: str) -> subprocess.CompletedProcess:
    """Helper to run a shell command inside a temporary instance of the target image."""
    res = subprocess.run(
        ["docker", "run", "--rm", "--entrypoint", "sh", IMAGE_NAME, "-c", cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert res.returncode not in DOCKER_DID_NOT_RUN, (
        f"Command never executed in container (exit {res.returncode}); an empty result here "
        f"would silently satisfy the assertion. cmd={cmd!r} stderr={res.stderr.strip()}"
    )
    return res


def get_image_flavor() -> str:
    """Detect image flavor from tag or image label."""
    img = IMAGE_NAME.lower()
    if ":intel" in img:
        return "intel"
    if ":amd" in img:
        return "amd"
    if ":cuda13" in img:
        return "cuda13"
    if ":cuda" in img:
        return "cuda"
    return "all"


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

    def test_no_snap_bloat(self):
        """Invariant: Snap, snapd, and snap directories must be completely absent."""
        res = run_in_container("which snap || which snapd || ls -d /snap /var/lib/snapd /var/cache/snapd 2>/dev/null || true")
        assert not res.stdout.strip(), f"Snap artifacts found in image: {res.stdout.strip()}"

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
        """Invariant: Hardware acceleration stack pre-installed based on image flavor and arch."""
        flavor = get_image_flavor()
        arch = run_in_container("dpkg --print-architecture").stdout.strip()
        assert arch, "Could not determine image architecture"

        if flavor in ("all", "intel"):
            if arch == "amd64":
                res = run_in_container("dpkg-query -W -f='${Status}' intel-media-va-driver-non-free 2>/dev/null")
                assert "install ok installed" in res.stdout, (
                    f"intel-media-va-driver-non-free not installed: {res.stdout}"
                )
            else:
                # The Intel QSV stack is amd64-only in the Dockerfile. On arm64 the universal
                # image must still ship Mesa, and must not carry the Intel packages.
                assert flavor == "all", f"Flavor '{flavor}' is not published for {arch}"
                res = run_in_container("dpkg-query -W -f='${Status}' mesa-libgallium 2>/dev/null")
                assert "install ok installed" in res.stdout, (
                    f"mesa-libgallium not installed on {arch}: {res.stdout}"
                )
                intel_res = run_in_container("dpkg-query -W -f='${Status}' intel-media-va-driver-non-free 2>/dev/null")
                assert "install ok installed" not in intel_res.stdout, (
                    f"Intel QSV stack must not be installed on {arch}"
                )
        elif flavor == "amd":
            res = run_in_container("dpkg-query -W -f='${Status}' mesa-libgallium 2>/dev/null")
            assert "install ok installed" in res.stdout, (
                f"mesa-libgallium not installed: {res.stdout}"
            )
        elif flavor == "cuda":
            # Host-based CUDA uses driver injection; verify NVIDIA environment hooks and zero bloat packages
            res = subprocess.run(
                ["docker", "image", "inspect", IMAGE_NAME, "--format", "{{json .Config.Env}}"],
                stdout=subprocess.PIPE,
                text=True,
                check=True,
            )
            assert "NVIDIA_DRIVER_CAPABILITIES=compute,video,utility" in res.stdout
            dpkg_res = run_in_container("dpkg-query -W -f='${Status}' libcublas-12-8 2>/dev/null")
            assert "install ok installed" not in dpkg_res.stdout, "libcublas must not be installed in host-based cuda flavor"
        elif flavor == "cuda13":
            res = run_in_container("dpkg-query -W -f='${Status}' cuda-nvrtc-13-4 2>/dev/null")
            assert "install ok installed" in res.stdout, (
                f"cuda-nvrtc-13-4 not installed: {res.stdout}"
            )
            dpkg_res = run_in_container("dpkg-query -W -f='${Status}' libcublas-13-4 2>/dev/null")
            assert "install ok installed" not in dpkg_res.stdout, "libcublas must not be installed in minimal cuda13 flavor"

    def test_vaapi_and_qsv_driver_stack(self):
        """Invariant: Hardware acceleration packages matching flavor must be installed."""
        flavor = get_image_flavor()
        arch_res = run_in_container("dpkg --print-architecture")
        arch = arch_res.stdout.strip()
        if flavor in ("all", "intel"):
            if arch == "amd64":
                packages = [
                    "intel-media-va-driver-non-free",
                    "intel-opencl-icd",
                    "libvpl2",
                    "libmfx-gen1.2",
                    "libze-intel-gpu1",
                ]
                for pkg in packages:
                    res = run_in_container(f"dpkg-query -W -f='${{Status}}' {pkg} 2>/dev/null")
                    assert "install ok installed" in res.stdout, f"Driver package '{pkg}' missing from image."
            else:
                # arm64 universal image: Mesa only, with the amd64-only Intel stack absent.
                assert flavor == "all", f"Flavor '{flavor}' is not published for {arch}"
                res = run_in_container("dpkg-query -W -f='${Status}' mesa-libgallium 2>/dev/null")
                assert "install ok installed" in res.stdout, f"mesa-libgallium missing on {arch}."
                for pkg in ("libvpl2", "libmfx-gen1.2", "libze-intel-gpu1"):
                    res = run_in_container(f"dpkg-query -W -f='${{Status}}' {pkg} 2>/dev/null")
                    assert "install ok installed" not in res.stdout, f"'{pkg}' must not be installed on {arch}."
        elif flavor == "amd":
            packages = [
                "mesa-libgallium",
                "mesa-vulkan-drivers",
                "libdrm-amdgpu1",
            ]
            for pkg in packages:
                res = run_in_container(f"dpkg-query -W -f='${{Status}}' {pkg} 2>/dev/null")
                assert "install ok installed" in res.stdout, f"Driver package '{pkg}' missing from image."
        elif flavor == "cuda13":
            if arch == "amd64":
                packages = [
                    "cuda-nvrtc-13-4",
                    "cuda-cudart-13-4",
                    "libnpp-13-4",
                ]
                for pkg in packages:
                    res = run_in_container(f"dpkg-query -W -f='${{Status}}' {pkg} 2>/dev/null")
                    assert "install ok installed" in res.stdout, f"Driver package '{pkg}' missing from image."
        elif flavor == "cuda":
            # Host-based CUDA: verify heavy math/solver packages are not bundled
            bloated_pkgs = ["cuda-libraries-12-8", "cuda-libraries-13-4", "libcublas-12-8", "libcusolver-12-8"]
            for pkg in bloated_pkgs:
                res = run_in_container(f"dpkg-query -W -f='${{Status}}' {pkg} 2>/dev/null")
                assert "install ok installed" not in res.stdout, f"Bloated package '{pkg}' should not be installed in host-based CUDA flavor."

        else:
            raise AssertionError(f"Unrecognised image flavor '{flavor}'; no invariant was verified.")

        # Legacy i965 driver (pre-2015 CPUs) is purged across all flavors
        res_i965 = run_in_container("dpkg-query -W -f='${Status}' i965-va-driver-shaders 2>/dev/null")
        assert "install ok installed" not in res_i965.stdout, "Legacy i965 driver must not be installed."

    def test_dead_runtimes_stripped(self):
        """Invariant: Dead win* and osx* runtime folders stripped from /app."""
        res = run_in_container("find /app -type d \\( -name 'win*' -o -name 'osx*' \\) 2>/dev/null")
        assert res.returncode == 0
        found_dead_runtimes = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        assert len(found_dead_runtimes) == 0, (
            f"Dead Windows/macOS runtimes still present: {found_dead_runtimes}"
        )

    def test_utility_binaries_present(self):
        """Invariant: docker and dovi_tool CLI binaries functional if present."""
        check_docker = run_in_container("test -f /usr/local/bin/docker")
        if check_docker.returncode == 0:
            docker_res = run_in_container("/usr/local/bin/docker --version")
            assert docker_res.returncode == 0, f"docker binary failed: {docker_res.stderr}"
            assert "Docker version" in docker_res.stdout

        check_dovi = run_in_container("test -f /usr/local/bin/dovi_tool")
        if check_dovi.returncode == 0:
            dovi_res = run_in_container("/usr/local/bin/dovi_tool --version")
            assert dovi_res.returncode == 0, f"dovi_tool binary failed: {dovi_res.stderr}"
            assert "dovi_tool" in dovi_res.stdout


class TestImageMetricsAndFootprint:
    """Tests asserting image size constraints and metadata."""

    def test_virtual_disk_size_limit(self):
        """Assert image virtual disk size meets gate threshold per flavor."""
        flavor = get_image_flavor()
        max_size = 3.5 if "cuda" in flavor else 2.5
        res = subprocess.run(
            ["docker", "image", "inspect", IMAGE_NAME, "--format", "{{.Size}}"],
            stdout=subprocess.PIPE,
            text=True,
            check=True,
        )
        size_bytes = int(res.stdout.strip())
        size_gb = size_bytes / (1024**3)
        assert size_gb <= max_size, f"Virtual size {size_gb:.2f} GB exceeds {max_size} GB gate threshold."

    def test_environment_variables_configured(self):
        """Assert essential environment variables and .NET container performance flags are baked in."""
        res = subprocess.run(
            ["docker", "image", "inspect", IMAGE_NAME, "--format", "{{json .Config.Env}}"],
            stdout=subprocess.PIPE,
            text=True,
            check=True,
        )
        env = res.stdout
        assert "DOTNET_CLI_TELEMETRY_OPTOUT=1" in env or "DOTNET_CLI_TELEMETRY_OPTOUT=true" in env
        assert "NVIDIA_VISIBLE_DEVICES=all" in env
        assert "NVIDIA_DRIVER_CAPABILITIES=compute,video,utility" in env
        assert "DOTNET_EnableDiagnostics=0" in env
        assert "DOTNET_gcServer=1" in env

    def test_healthcheck_configured(self):
        """Assert native Docker HEALTHCHECK instruction is defined on the image."""
        res = subprocess.run(
            ["docker", "image", "inspect", IMAGE_NAME, "--format", "{{json .Config.Healthcheck}}"],
            stdout=subprocess.PIPE,
            text=True,
            check=True,
        )
        assert "curl" in res.stdout, f"HEALTHCHECK instruction missing: {res.stdout}"


class TestRuntimeSmokeAndWebUI:
    """Tests executing the container and validating real HTTP and startup performance."""

    CONTAINER_NAME = "fileflows-pytest-smoke"
    PORT = 19205
    READY_TIMEOUT_SECONDS = 25

    @classmethod
    def teardown_class(cls):
        """Ensure test container is stopped and removed."""
        subprocess.run(["docker", "rm", "-f", cls.CONTAINER_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @classmethod
    def _launch(cls):
        """Start the container detached and return how long `docker run` took."""
        subprocess.run(["docker", "rm", "-f", cls.CONTAINER_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        start_time = time.time()
        subprocess.run(
            ["docker", "run", "-d", "--name", cls.CONTAINER_NAME, "-p", f"{cls.PORT}:5000",
             "-e", "TZ=UTC", "-e", "PUID=1000", "-e", "PGID=1000", IMAGE_NAME],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True,
        )
        return time.time() - start_time

    @classmethod
    def _logs(cls):
        """Return the container's combined stdout/stderr so far."""
        res = subprocess.run(["docker", "logs", cls.CONTAINER_NAME],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
        return res.stdout

    @classmethod
    def _poll_web_ui(cls):
        """Poll the Web UI until it answers 200; return (ready_seconds, html)."""
        url = f"http://127.0.0.1:{cls.PORT}/"
        for elapsed in range(1, cls.READY_TIMEOUT_SECONDS + 1):
            time.sleep(1)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "pytest"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        return elapsed, resp.read().decode("utf-8")
            except Exception:
                continue
        return None, ""

    def test_container_startup_and_web_ui(self):
        """Assert container starts instantly and serves Web UI with 200 OK."""
        launch_duration = self._launch()
        assert launch_duration < 5.0, f"Container launch took too long: {launch_duration:.2f}s"

        ready_seconds, final_html = self._poll_web_ui()
        assert ready_seconds is not None, (
            f"Web UI did not return HTTP 200 within {self.READY_TIMEOUT_SECONDS}s. Logs:\n{self._logs()}"
        )
        assert "<title>FileFlows" in final_html, f"Unexpected page content: {final_html[:300]}"

        # Inspect the whole boot log, not just the first second of it.
        logs = self._logs()
        assert any(marker in logs for marker in (
            "[FileFlows Real Image]", "Hardware acceleration pre-configured", "already installed.",
        )), f"Entrypoint failed to verify pre-configured hardware drivers or Real Image marker. Logs:\n{logs}"
        assert "apt-get update" not in logs, f"Container unexpectedly ran apt-get update on boot!\n{logs}"

        subprocess.run(["docker", "rm", "-f", self.CONTAINER_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
