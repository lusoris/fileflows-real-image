---
name: lint-all
description: Run Hadolint, Yamllint, ShellCheck, codespell, gitleaks, and documentation consistency tests in parallel.
---

# /lint-all

Executes all repository static analysis tools, linters, format checks, and documentation invariant tests.

## Invocation

```bash
/lint-all [--fix]
```

## Steps

1. **Dockerfile Linting**:

   ```bash
   hadolint --config .hadolint.yaml Dockerfile
   ```

2. **YAML Formatting & Linting**:

   ```bash
   yamllint -c .yamllint.yml .
   ```

3. **Shell Script Verification**:

   ```bash
   shellcheck tests/run_tests.sh
   ```

4. **Pre-commit Quality Hooks**:

   ```bash
   pre-commit run --all-files
   ```

5. **Documentation & Anchor Consistency**:

   ```bash
   pytest tests/test_docs_consistency.py -v --tb=short
   ```

6. **Dockerfile Mirror Alignment**:

   ```bash
   cmp -s Dockerfile Dockerfile.optimized || { echo "Drift detected between Dockerfile and Dockerfile.optimized"; exit 1; }
   ```

## Guardrails

- All tests must pass cleanly with 0 warnings or errors before pushing to `main`.
- With `--fix`, pre-commit hooks will automatically fix trailing whitespace and end-of-file newlines.
