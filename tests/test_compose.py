"""Test suite verifying Docker Compose production deployment specification and hardening."""

from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"


class TestDockerCompose:
    """Assertions ensuring docker-compose.yml complies with Compose specifications and security guidelines."""

    def test_compose_file_exists_and_valid_yaml(self):
        """Assert docker-compose.yml exists and parses cleanly."""
        assert COMPOSE_FILE.exists(), "docker-compose.yml must exist"
        data = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
        assert isinstance(data, dict), "Compose file must parse to a dictionary"
        assert "services" in data, "Compose file missing 'services' definition"
        assert "fileflows" in data["services"], "Compose file missing 'fileflows' service"

    def test_fileflows_service_configuration(self):
        """Assert core container configuration and operational flags on fileflows service."""
        data = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
        svc = data["services"]["fileflows"]

        assert "image" in svc
        assert "ghcr.io/lusoris/fileflows-real-image" in svc["image"]
        assert svc.get("restart") == "unless-stopped"
        assert svc.get("init") is True

        # Ports
        ports = svc.get("ports", [])
        assert any(":5000" in p for p in ports), "Service must expose port 5000"

        # Environment variables
        env = svc.get("environment", [])
        assert any("PUID" in e for e in env), "PUID environment variable missing"
        assert any("PGID" in e for e in env), "PGID environment variable missing"
        assert any("TZ" in e for e in env), "TZ environment variable missing"

    def test_volumes_and_mounts(self):
        """Assert required volume mounts for data, temp, and logs are declared."""
        data = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
        svc = data["services"]["fileflows"]
        volumes = svc.get("volumes", [])

        # Check container destination mount points
        mount_points = [v.split(":")[1] for v in volumes if ":" in v]
        assert "/app/Data" in mount_points
        assert "/temp" in mount_points
        assert "/app/Logs" in mount_points

        # Check top-level named volumes declaration
        declared_volumes = data.get("volumes", {})
        assert "fileflows-data" in declared_volumes
        assert "fileflows-temp" in declared_volumes
        assert "fileflows-logs" in declared_volumes

    def test_security_hardening_directives(self):
        """Assert security hardening options: no-new-privileges and bounded cap_add/cap_drop."""
        data = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
        svc = data["services"]["fileflows"]

        sec_opt = svc.get("security_opt", [])
        assert "no-new-privileges:true" in sec_opt

        cap_drop = svc.get("cap_drop", [])
        assert "ALL" in cap_drop

        cap_add = svc.get("cap_add", [])
        assert "CHOWN" in cap_add
        assert "SETUID" in cap_add
        assert "SETGID" in cap_add
