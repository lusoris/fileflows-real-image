"""Automated verification suite enforcing the NASA/JPL Power of 10 engineering standards."""

import ast
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"
SCRIPTS_DIR = REPO_ROOT / "scripts"
DOCS_DIR = REPO_ROOT / "docs"
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"


class TestNASAPowerOfTen:
    """Assertions codifying and enforcing NASA/JPL Power of 10 safety and quality rules."""

    def test_rule1_shell_strict_error_handling(self):
        """Rule 1 & 7: All shell scripts must enforce strict error handling via set -euo pipefail."""
        shell_scripts = list(TESTS_DIR.glob("*.sh"))
        assert len(shell_scripts) > 0, "Expected at least one shell script under tests/"

        for script in shell_scripts:
            content = script.read_text(encoding="utf-8")
            assert "set -euo pipefail" in content or "set -e" in content, (
                f"Shell script {script.name} must declare 'set -euo pipefail' or 'set -e'"
            )

    def test_rule2_bounded_polling_loops(self):
        """Rule 2: Every loop must carry a statically provable upper bound."""
        test_image_file = TESTS_DIR / "test_image.py"
        assert test_image_file.exists(), "tests/test_image.py must exist"

        unbounded = []
        bounded_polls = 0
        for py_file in sorted(TESTS_DIR.glob("test_*.py")) + sorted(SCRIPTS_DIR.glob("*.py")):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.While):
                    # Only `while <literal-false-able>` is acceptable; `while True` never terminates
                    # by its own condition, so the bound would live outside the loop construct.
                    unbounded.append(f"{py_file.name}:{node.lineno} while-loop without a static bound")
                if isinstance(node, ast.For) and isinstance(node.iter, ast.Call):
                    if getattr(node.iter.func, "id", None) == "range" and py_file == test_image_file:
                        bounded_polls += 1

        assert not unbounded, "Unbounded loops are strictly prohibited (Rule 2):\n" + "\n".join(unbounded)
        assert bounded_polls > 0, "Runtime smoke test must poll via a bounded range() loop."

    def test_rule4_short_functions(self):
        """Rule 4: Every function, in test suites and production scripts alike, stays <= 60 lines."""
        python_files = sorted(TESTS_DIR.glob("test_*.py")) + sorted(SCRIPTS_DIR.glob("*.py"))
        assert python_files, "Expected Python sources under tests/ and scripts/"
        assert any(f.parent == SCRIPTS_DIR for f in python_files), (
            "Production scripts must be in scope for Rule 4, not only the test suite"
        )

        long_functions = []
        for py_file in python_files:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    lines = node.end_lineno - node.lineno + 1
                    if lines > 60:
                        long_functions.append(f"{py_file.name}::{node.name} ({lines} lines > 60 limit)")

        assert not long_functions, "Functions exceeding 60-line bound (Rule 4):\n" + "\n".join(long_functions)

    def test_rule5_assertion_density(self):
        """Rule 5: Average assertion density across all test functions must be >= 2.0."""
        total_assertions = 0
        total_test_functions = 0
        per_suite_stats = {}

        for py_file in TESTS_DIR.glob("test_*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            file_assertions = 0
            file_tests = 0

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                    file_tests += 1
                    func_assertions = sum(1 for child in ast.walk(node) if isinstance(child, ast.Assert))
                    file_assertions += func_assertions

            if file_tests > 0:
                per_suite_stats[py_file.name] = (file_assertions, file_tests)
                total_assertions += file_assertions
                total_test_functions += file_tests

        avg_density = total_assertions / total_test_functions if total_test_functions > 0 else 0
        print(f"\n[NASA Rule 5] Total assertions: {total_assertions}, Total tests: {total_test_functions}, Average density: {avg_density:.2f} asserts/test")
        assert avg_density >= 2.0, (
            f"Average assertion density {avg_density:.2f} < 2.0 threshold! "
            f"Stats: {total_assertions} asserts across {total_test_functions} tests.\n{per_suite_stats}"
        )

    def test_rule6_least_privilege_and_cap_drop(self):
        """Rule 6: Container deployments must drop ALL capabilities and enable no-new-privileges."""
        assert COMPOSE_FILE.exists()
        data = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
        svc = data["services"]["fileflows"]

        sec_opt = svc.get("security_opt", [])
        assert "no-new-privileges:true" in sec_opt

        cap_drop = svc.get("cap_drop", [])
        assert "ALL" in cap_drop

        # Verify dangerous capabilities are never added
        forbidden_caps = ["SYS_ADMIN", "NET_ADMIN", "SYS_RAWIO", "SYS_PTRACE"]
        cap_add = svc.get("cap_add", [])
        for forbidden in forbidden_caps:
            assert forbidden not in cap_add, f"Dangerous capability '{forbidden}' found in cap_add"

    def test_rule8_declarative_restraint(self):
        """Rule 8: Shell scripts must not use arbitrary dynamic eval."""
        for script in TESTS_DIR.glob("*.sh"):
            content = script.read_text(encoding="utf-8")
            assert "eval " not in content, f"Shell script {script.name} uses forbidden 'eval'"

    def test_rule10_principles_documented_and_in_nav(self):
        """Rule 10: docs/principles.md must exist and be registered in mkdocs.yml navigation."""
        principles_file = DOCS_DIR / "principles.md"
        assert principles_file.exists(), "docs/principles.md must exist"

        mkdocs_file = REPO_ROOT / "mkdocs.yml"
        content = mkdocs_file.read_text(encoding="utf-8")
        assert "principles.md" in content, "docs/principles.md must be linked in mkdocs.yml navigation"
