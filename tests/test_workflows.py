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
        for wf in sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml")):
            data = yaml.safe_load(wf.read_text(encoding="utf-8"))
            env = data.get("env", {})
            assert env.get("FORCE_JAVASCRIPT_ACTIONS_TO_NODE24") == "true", (
                f"Workflow {wf.name} must set env FORCE_JAVASCRIPT_ACTIONS_TO_NODE24 to 'true'"
            )

    def test_concurrency_groups_configured(self):
        """Assert all workflows configure concurrency groups."""
        for wf in sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml")):
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

    @staticmethod
    def _job_step_names(job):
        """Collect a job's step names, following a local reusable-workflow delegation."""
        if "uses" in job:
            # removeprefix, not lstrip: lstrip("./") strips a character set and would
            # eat the leading dot of ".github".
            target = job["uses"].split("@")[0].removeprefix("./")
            called = REPO_ROOT / target
            assert called.exists(), f"Reusable workflow '{job['uses']}' does not exist at {called}"
            called_data = yaml.safe_load(called.read_text(encoding="utf-8"))
            return [
                step.get("name", "")
                for called_job in called_data.get("jobs", {}).values()
                for step in called_job.get("steps", [])
            ]
        return [step.get("name", "") for step in job.get("steps", [])]

    def test_ci_workflow_quality_gates(self):
        """Assert ci.yml runs all required static analysis and verification steps."""
        ci_wf = WORKFLOWS_DIR / "ci.yml"
        assert ci_wf.exists()
        data = yaml.safe_load(ci_wf.read_text(encoding="utf-8"))

        jobs = data.get("jobs", {})
        assert "lint" in jobs, "ci.yml missing 'lint' job"
        assert "test-and-assert" in jobs, "ci.yml missing 'test-and-assert' job"

        lint_steps = self._job_step_names(jobs["lint"])
        assert any("Hadolint" in s for s in lint_steps), "Hadolint step missing from ci.yml"
        assert any("Yamllint" in s for s in lint_steps), "Yamllint step missing from ci.yml"
        assert any("Offline Unit" in s or "Consistency" in s for s in lint_steps), (
            "Offline Unit & Consistency test step missing from ci.yml"
        )
        assert any("ShellCheck" in s for s in lint_steps), "ShellCheck step missing from ci.yml"
        assert any("pre-commit" in s for s in lint_steps), "pre-commit step missing from ci.yml"

    def test_release_is_gated_on_quality_checks(self):
        """Invariant: no release path may build or push without first clearing the offline gates.

        The scheduled 6-hourly trigger previously reached the build and GHCR push having run
        no tests at all, because the release workflow was fully independent of CI.
        """
        release_wf = WORKFLOWS_DIR / "build-and-release.yml"
        data = yaml.safe_load(release_wf.read_text(encoding="utf-8"))
        jobs = data.get("jobs", {})

        release_job = jobs.get("check-and-release")
        assert release_job is not None, "build-and-release.yml missing 'check-and-release' job"

        needs = release_job.get("needs", [])
        needs = [needs] if isinstance(needs, str) else needs
        assert needs, "check-and-release must not run before the quality gates"

        for gate in needs:
            assert gate in jobs, f"check-and-release needs unknown job '{gate}'"
            gate_steps = self._job_step_names(jobs[gate])
            assert gate_steps, f"Gate job '{gate}' runs no steps"

        gating_steps = [s for gate in needs for s in self._job_step_names(jobs[gate])]
        assert any("Offline Unit" in s or "Consistency" in s for s in gating_steps), (
            f"Release gate runs no offline test step; gate steps were: {gating_steps}"
        )

    def test_docs_workflow_strict_mode(self):
        """Assert docs.yml executes mkdocs build with --strict."""
        docs_wf = WORKFLOWS_DIR / "docs.yml"
        assert docs_wf.exists()
        content = docs_wf.read_text(encoding="utf-8")
        assert "mkdocs build --strict" in content, "docs.yml must build with --strict flag"
