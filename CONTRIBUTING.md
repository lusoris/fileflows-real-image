# Contributing to FileFlows Real Image

Thank you for your interest in improving this image!

## Pull Request Guidelines

1. **Keep Builds Self-Contained**:
   - The `Dockerfile` must build directly from upstream without requiring local host folders or pre-extracted assets.
2. **Conventional Commits**:
   - We follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `perf:`, `ci:`, `docs:`, `chore:`) to structure changelogs and upstream-anchored release tags.
3. **Validate Locally**:
   - Run the local assertion and doc consistency suite before submitting:
     ```bash
     # Build image
     docker build -t ghcr.io/lusoris/fileflows-real-image:latest .

     # Run complete test & doc consistency suite
     pytest tests/ -v --tb=short
     ```
4. **Zero Base CVE Policy**:
   - Run `docker scout cves` or `trivy` on the built image to ensure no new base-image vulnerabilities are introduced.
