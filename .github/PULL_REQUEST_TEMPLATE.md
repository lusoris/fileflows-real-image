## Pull Request

### Summary
<!-- What changed, why, and which issue it addresses. -->

- 

### Verification & Testing
- [ ] Image builds cleanly without local dependencies: `docker build -t revenz/fileflows:optimized .`
- [ ] Complete pytest suite & doc consistency checks pass: `pytest tests/ -v`
- [ ] Container launches and serves web UI on port 19200 (`curl -I http://localhost:19200/initial-config`)
- [ ] Hardware acceleration packages verified (`vainfo`)
- [ ] Base CVE count checked (`trivy` or `docker scout cves`)

```bash
# Output or command log
```
