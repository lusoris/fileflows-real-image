# Contributing to FileFlows Real Image

Thank you for your interest in improving this image!

## Pull Request Guidelines

1. **Keep Builds Self-Contained**:
   - The `Dockerfile` must build directly from upstream without requiring local host folders or pre-extracted assets.
2. **Conventional Commits**:
   - We use [Conventional Commits](https://www.conventionalcommits.org/) to power automated changelog generation and [Release Please](https://github.com/googleapis/release-please):
     - `feat:` New capability or build feature.
     - `fix:` Bug fix or vulnerability remediation.
     - `perf:` Image size or build speed optimization.
     - `ci:` Changes to GitHub Actions workflows.
     - `docs:` Documentation improvements.
     - `chore:` Routine maintenance.
3. **Validate Locally**:
   - Run a local test build before submitting:
     ```bash
     docker build -t test-build .
     docker run --rm -d -p 5000:5000 --name test-container test-build
     curl -s -I http://localhost:5000/
     docker rm -f test-container
     ```
4. **Zero Base CVE Policy**:
   - Run `docker scout cves` or `trivy` on the built image to ensure no new base-image vulnerabilities are introduced.
