<!-- markdownlint-disable MD013 -->
# Engineering Principles — NASA/JPL Power of 10

> Authoritative engineering standards for **FileFlows Real Image**. These principles adapt the NASA/JPL Laboratory for Reliable Software ("The Power of 10: Rules for Developing Safety-Critical Code") for containerized OCI infrastructure, shell scripts, and automated test engineering.

---

## §1. The Power of 10 (Adapted for OCI & Infrastructure)

Every change merged to `main` must adhere to these ten rules. Automated verification in `tests/test_principles.py` enforces these constraints across code, build definitions, and test suites.

### Rule 1: Simple Control Flow
- Avoid complex, unstructured branching or dynamic execution in shell scripts and entrypoints.
- Shell scripts must declare `set -euo pipefail` at the start.
- Docker multi-stage builds must follow a strictly linear DAG (directed acyclic graph) without circular or redundant intermediate stage dependencies.

### Rule 2: Bounded Loops & Timeouts
- Every loop, retry mechanism, polling loop, and healthcheck must have a statically verifiable upper bound.
- No unbounded `while true` polling without a timeout or counter limit.
- Container healthchecks must explicitly define `--interval`, `--timeout`, and `--retries` (e.g. `--retries=3 --timeout=5s`).
- Test runners and smoke tests must enforce finite wait loops (maximum 25 iterations with fixed sleep delays).

### Rule 3: Pre-allocated Footprint (No Runtime Allocations)
- Hardware acceleration drivers and runtime dependencies must be pre-baked into the image at build time.
- Containers must never execute dynamic package manager commands (`apt-get update`, `apt-get install`) during container boot.
- Eliminate bloat dynamically during build stages and squash layer history via `FROM scratch COPY --from=base-selected / /`.

### Rule 4: Short Functions
- Function bodies in Python test suites and shell scripts must not exceed **60 lines** (a single standard display screen).
- Test functions must be focused, single-purpose, and clearly documented.

### Rule 5: High Assertion Density
- Test suites must maintain an average **assertion density of at least 2.0 assertions per function**.
- Assertions must verify multiple orthogonal conditions: exit codes, output strings, filesystem state, and absence of error indicators.

### Rule 6: Smallest Scope & Least Privilege
- Restrict data objects and variables to the smallest possible scope.
- In container deployments (`docker-compose.yml`), container processes must run under least-privilege constraints:
  - `security_opt: [no-new-privileges:true]`
  - `cap_drop: [ALL]`
  - Explicitly bounding `cap_add` strictly to required capabilities (`CHOWN`, `SETUID`, `SETGID`, `DAC_OVERRIDE`).

### Rule 7: Check Every Return Value
- Every fallible system call, subprocess invocation, or API request must have its return value explicitly checked.
- In shell scripts, failures must abort execution immediately via `set -e` or trap handlers.
- In Python tests, subprocess calls must verify `res.returncode == 0` or execute with `check=True`.

### Rule 8: Declarative Restraint
- Build definitions ([Dockerfile](../Dockerfile)) and deployment manifests ([docker-compose.yml](../docker-compose.yml)) must remain purely declarative.
- Avoid runtime `eval`, dynamic string execution, or untracked environment variable overrides.

### Rule 9: Direct Hooks & Zero Indirection
- Avoid unnecessary translation layers, wrappers, or nested emulators.
- NVIDIA GPU hardware transcoding (`:cuda`) relies on direct host-injected driver hooks (`libcuda.so.1`, `libnvidia-encode.so.1`, `libnvcuvid.so.1`) via NVIDIA Container Toolkit with zero in-container package bloat.
- AMD GPU transcoding (`:amd`) connects directly to the kernel DRM layer via Mesa Gallium VA-API (`radeonsi`) and RADV Vulkan without heavy compute runtimes.

### Rule 10: Zero Findings at Maximum Strictness
- All linters, static analyzers, and quality gates must pass with **zero warnings / zero findings**:
  - Hadolint (`.hadolint.yaml`): 0 errors on Dockerfile.
  - Yamllint (`.yamllint.yml`): 0 warnings across all YAML files.
  - ShellCheck: 0 issues on all `.sh` scripts.
  - Codespell: 0 typos or misspelled identifiers.
  - Gitleaks: 0 secret or credential findings.
  - Pre-commit: 100% clean across all configured hooks.
- Automated test coverage must maintain **>= 95%** statement coverage on all offline test suites.

---

## §2. Quality Gates & Enforcement

| Quality Gate | Tooling / Check | Enforcement Level |
| :--- | :--- | :--- |
| **Assertion Density** | `tests/test_principles.py` (AST inspection) | Average >= 2.0 asserts per test |
| **Function Length** | `tests/test_principles.py` (AST line count) | <= 60 lines per function |
| **Shell Strictness** | `tests/test_principles.py` + `shellcheck` | `set -euo pipefail` required |
| **Least Privilege** | `tests/test_compose.py` + `tests/test_principles.py` | `cap_drop: [ALL]` + `no-new-privileges` |
| **Test Coverage** | `pytest --cov=tests` | >= 85% required floor (targeting >= 95%) |
| **Dockerfile Mirror** | `cmp -s Dockerfile Dockerfile.optimized` | 100% byte-identical |
