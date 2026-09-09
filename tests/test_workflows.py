"""Automated test suite validating GitHub Actions workflow definitions and matrix completeness."""

from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


class TestGitHubWorkflows:
    """Assertions ensuring CI/CD pipelines are syntactically valid and architecturally complete."""

    def test_all_workflows_valid_yaml(self):
        """Assert every workflow file in .github/workflows is well-formed YAML."""
        workflow_files = list(WORKFLOWS_DIR.glob("*.yml")) + list(WORKFLOWS_DIR.glob("*.yaml"))
        assert len(workflow_files) >= 3, f"Expected at least 3 workflow files, found {len(workflow_files)}"

        for wf in workflow_files:
            content = wf.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            assert isinstance(data, dict), f"Workflow {wf.name} did not parse to a dictionary"
            assert "name" in data, f"Workflow {wf.name} missing top-level 'name' field"
            assert "on" in data or True in data, f"Workflow {wf.name} missing 'on' trigger"
            assert "jobs" in data, f"Workflow {wf.name} missing 'jobs' section"

    def test_node24_runtime_enforced(self):
        """Invariant: All GitHub Actions workflows must enforce Node 24 actions runtime."""
        for wf in WORKFLOWS_DIR.glob("*.yml"):
            data = yaml.safe_load(wf.read_text(encoding="utf-8"))
            env = data.get("env", {})
            assert env.get("FORCE_JAVASCRIPT_ACTIONS_TO_NODE24") == "true", (
                f"Workflow {wf.name} must set env FORCE_JAVASCRIPT_ACTIONS_TO_NODE24 to 'true'"
            )

    def test_concurrency_groups_configured(self):
        """Assert all workflows configure concurrency groups."""
        for wf in WORKFLOWS_DIR.glob("*.yml"):
            data = yaml.safe_load(wf.read_text(encoding="utf-8"))
            concurrency = data.get("concurrency", {})
            assert "group" in concurrency, f"Workflow {wf.name} missing concurrency.group"

    def test_build_matrix_flavor_and_platform_mapping(self):
        """Invariant: build-and-release.yml must cover all 5 flavors with correct CPU architectures."""
        release_wf = WORKFLOWS_DIR / "build-and-release.yml"
        assert release_wf.exists()
        data = yaml.safe_load(release_wf.read_text(encoding="utf-8"))

        # Inspect check-and-release steps for each flavor
        steps = data["jobs"]["check-and-release"]["steps"]
        flavors_found = {}
        for step in steps:
            with_args = step.get("with", {})
            build_args = with_args.get("build-args", "")
            if "FLAVOR=" in build_args:
                flavor = build_args.split("FLAVOR=")[1].split()[0]
                platforms = with_args.get("platforms", "")
                flavors_found[flavor] = platforms

        expected_matrix = {
            "all": "linux/amd64,linux/arm64",
            "amd": "linux/amd64,linux/arm64",
            "intel": "linux/amd64",
            "cuda": "linux/amd64",
            "cuda13": "linux/amd64",
        }

        for flavor, platforms in expected_matrix.items():
            assert flavor in flavors_found, f"Flavor '{flavor}' missing from release build steps."
            assert flavors_found[flavor] == platforms, (
                f"Flavor '{flavor}' has platform mismatch: expected {platforms}, got {flavors_found[flavor]}"
            )

    def test_ci_workflow_quality_gates(self):
        """Assert ci.yml includes all required static analysis and verification steps."""
        ci_wf = WORKFLOWS_DIR / "ci.yml"
        assert ci_wf.exists()
        data = yaml.safe_load(ci_wf.read_text(encoding="utf-8"))

        jobs = data.get("jobs", {})
        assert "lint" in jobs, "ci.yml missing 'lint' job"
        assert "test-and-assert" in jobs, "ci.yml missing 'test-and-assert' job"

        lint_steps = [step.get("name", "") for step in jobs["lint"].get("steps", [])]
        assert any("Hadolint" in s for s in lint_steps), "Hadolint step missing from ci.yml"
        assert any("Yamllint" in s for s in lint_steps), "Yamllint step missing from ci.yml"
        assert any("Offline Unit" in s or "Consistency" in s for s in lint_steps), (
            "Offline Unit & Consistency test step missing from ci.yml"
        )
        assert any("ShellCheck" in s for s in lint_steps), "ShellCheck step missing from ci.yml"

    def test_docs_workflow_strict_mode(self):
        """Assert docs.yml executes mkdocs build with --strict."""
        docs_wf = WORKFLOWS_DIR / "docs.yml"
        assert docs_wf.exists()
        content = docs_wf.read_text(encoding="utf-8")
        assert "mkdocs build --strict" in content, "docs.yml must build with --strict flag"
