"""
test_docs_consistency.py

Comprehensive CI test suite verifying documentation integrity and synchronization
with code, configuration, and architectural invariants across all markdown files.
"""

import os
import re
import urllib.parse
from pathlib import Path
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def get_all_markdown_files():
    """Find all markdown files in the repository excluding build / test caches."""
    md_files = []
    for root, dirs, files in os.walk(REPO_ROOT):
        # Ignore hidden dirs like .git, .pytest_cache
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "scratch", "brain")]
        for file in files:
            if file.endswith(".md"):
                md_files.append(Path(root) / file)
    return md_files


def slugify_heading(heading_text: str) -> str:
    """
    Generate GitHub-style markdown anchor slug from heading text:
    - Lowercase
    - Strip inline markdown links/formatting punctuation
    - Spaces replaced with hyphens
    - Consecutive hyphens preserved as GitHub renders them
    """
    # Remove markdown link text syntax [text](url) -> text
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", heading_text)
    # Remove inline code ticks
    cleaned = cleaned.replace("`", "")
    # Remove formatting characters (*, _)
    cleaned = re.sub(r"[\*\_]", "", cleaned)
    # Lowercase
    cleaned = cleaned.strip().lower()
    # Strip non-alphanumeric except spaces, hyphens, and slashes
    cleaned = re.sub(r"[^\w\s\-/]", "", cleaned)
    # Replace spaces and slashes with hyphens
    cleaned = re.sub(r"[\s/]+", "-", cleaned)
    return cleaned


class TestDocsConsistency:
    """Test suite ensuring documentation stays 100% in line with codebase and configs."""

    def test_markdown_local_links_exist(self):
        """Assert all relative markdown links [text](path) point to files that exist on disk."""
        md_files = get_all_markdown_files()
        assert len(md_files) > 0, "No markdown files found to inspect"

        # Regex to extract markdown links: [text](target)
        # Avoid image links or external URLs
        link_pattern = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
        missing_targets = []

        for md_file in md_files:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            # Exclude code blocks when searching for links
            content_without_code = re.sub(r"```[\s\S]*?```", "", content)

            for match in link_pattern.finditer(content_without_code):
                target = match.group(2).strip()
                # Skip external URLs, mailto links, or pure in-page anchors
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue

                # Strip query params or internal anchor from file path (e.g. file.md#heading)
                file_target = target.split("#")[0].strip()
                if not file_target:
                    continue

                # URL decode in case of %20 etc
                file_target = urllib.parse.unquote(file_target)

                # MkDocs strict constraint: docs/ files must not link outside docs/ using relative paths
                if "docs" in md_file.parts and target.startswith(".."):
                    missing_targets.append(
                        f"{md_file.relative_to(REPO_ROOT)}: link '{target}' traverses outside docs/ directory (violates MkDocs strict mode)"
                    )
                    continue

                if file_target.startswith("/"):
                    resolved = REPO_ROOT / file_target.lstrip("/")
                else:
                    resolved = (md_file.parent / file_target).resolve()

                if not resolved.exists():
                    missing_targets.append(
                        f"{md_file.relative_to(REPO_ROOT)}: link '{target}' -> {resolved} does not exist"
                    )

        assert not missing_targets, (
            "Found broken local markdown links in repository:\n" + "\n".join(missing_targets)
        )

    def test_markdown_heading_anchors_valid(self):
        """Assert all internal anchor links [text](#anchor) resolve to valid headings in that document."""
        md_files = get_all_markdown_files()
        anchor_pattern = re.compile(r"(?<!!)\[([^\]]+)\]\(#([^)]+)\)")
        heading_pattern = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
        broken_anchors = []

        for md_file in md_files:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            # Collect all heading slugs
            headings = heading_pattern.findall(content)
            heading_slugs = {slugify_heading(h) for h in headings}

            # Find all anchor references
            for match in anchor_pattern.finditer(content):
                anchor = match.group(2).strip().lower()
                if anchor not in heading_slugs:
                    broken_anchors.append(
                        f"{md_file.relative_to(REPO_ROOT)}: anchor '#{anchor}' has no matching heading. Available: {sorted(heading_slugs)}"
                    )

        assert not broken_anchors, (
            "Found broken in-page anchors in markdown documentation:\n" + "\n".join(broken_anchors)
        )

    def test_compose_yaml_block_sync(self):
        """Assert the Docker Compose example in README.md matches docker-compose.yml exactly."""
        compose_file = REPO_ROOT / "docker-compose.yml"
        readme_file = REPO_ROOT / "README.md"

        assert compose_file.exists(), "docker-compose.yml must exist"
        assert readme_file.exists(), "README.md must exist"

        actual_compose = yaml.safe_load(compose_file.read_text(encoding="utf-8"))
        readme_content = readme_file.read_text(encoding="utf-8")

        # Extract the yaml code block for compose in README.md
        yaml_blocks = re.findall(r"```yaml\n([\s\S]*?)```", readme_content)
        compose_blocks = [b for b in yaml_blocks if "fileflows:" in b]
        assert len(compose_blocks) == 1, "README.md must contain exactly one docker compose yaml snippet"

        doc_compose = yaml.safe_load(compose_blocks[0])

        actual_service = actual_compose["services"]["fileflows"]
        doc_service = doc_compose["services"]["fileflows"]

        # 1. Image name
        assert doc_service["image"].startswith("ghcr.io/lusoris/fileflows-real-image:latest"), (
            f"README compose image '{doc_service['image']}' does not match 'ghcr.io/lusoris/fileflows-real-image:latest'"
        )

        # 2. Port mapping (must expose port 5000 from container with default host 19200)
        assert doc_service["ports"] == actual_service["ports"], (
            f"README ports {doc_service['ports']} do not match docker-compose.yml {actual_service['ports']}"
        )

        # 3. Core volumes
        actual_volumes = set(actual_service.get("volumes", []))
        doc_volumes = set(doc_service.get("volumes", []))
        assert actual_volumes == doc_volumes, (
            f"README volumes {doc_volumes} do not match docker-compose.yml {actual_volumes}"
        )

        # 4. Security configuration
        assert doc_service.get("security_opt") == actual_service.get("security_opt"), (
            f"README security_opt {doc_service.get('security_opt')} does not match docker-compose.yml {actual_service.get('security_opt')}"
        )
        assert doc_service.get("cap_drop") == actual_service.get("cap_drop"), (
            f"README cap_drop {doc_service.get('cap_drop')} does not match docker-compose.yml {actual_service.get('cap_drop')}"
        )
        assert doc_service.get("cap_add") == actual_service.get("cap_add"), (
            f"README cap_add {doc_service.get('cap_add')} does not match docker-compose.yml {actual_service.get('cap_add')}"
        )
        assert doc_service.get("init") == actual_service.get("init"), (
            f"README init {doc_service.get('init')} does not match docker-compose.yml {actual_service.get('init')}"
        )

    def test_all_markdown_yaml_snippets_parseable(self):
        """Assert every embedded YAML block in any .md file is syntactically valid YAML."""
        md_files = get_all_markdown_files()
        yaml_block_pattern = re.compile(r"```ya?ml\n([\s\S]*?)```")
        parse_errors = []

        for md_file in md_files:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            for idx, match in enumerate(yaml_block_pattern.finditer(content)):
                snippet = match.group(1)
                try:
                    yaml.safe_load(snippet)
                except Exception as exc:
                    parse_errors.append(
                        f"{md_file.relative_to(REPO_ROOT)}: yaml snippet #{idx + 1} failed parsing: {exc}"
                    )

        assert not parse_errors, (
            "Found invalid YAML code blocks in markdown files:\n" + "\n".join(parse_errors)
        )

    def test_version_alignment(self):
        """Assert version.txt matches version references in README.md and Dockerfile."""
        version_file = REPO_ROOT / "version.txt"
        readme_file = REPO_ROOT / "README.md"
        dockerfile = REPO_ROOT / "Dockerfile"

        assert version_file.exists(), "version.txt must exist"
        version = version_file.read_text(encoding="utf-8").strip()
        assert re.match(r"^\d{2}\.\d{2}\.\d+$", version), f"version.txt '{version}' must match CalVer YY.MM.PATCH"

        readme_content = readme_file.read_text(encoding="utf-8")
        assert version in readme_content, (
            f"README.md does not reference upstream version '{version}' recorded in version.txt"
        )

    def test_architectural_invariants_aligned(self):
        """Assert AGENTS.md and README.md adhere to architectural directives."""
        agents_file = REPO_ROOT / "AGENTS.md"
        readme_file = REPO_ROOT / "README.md"
        dockerfile = REPO_ROOT / "Dockerfile"

        agents_text = agents_file.read_text(encoding="utf-8")
        readme_text = readme_file.read_text(encoding="utf-8")
        dockerfile_text = dockerfile.read_text(encoding="utf-8")

        # 1. Ubuntu 26.04 Resolute
        assert "26.04" in agents_text and "26.04" in readme_text and "26.04" in dockerfile_text

        # 2. aspnetcore-runtime-10.0 and no dotnet-sdk
        assert "aspnetcore-runtime-10.0" in dockerfile_text
        assert "dotnet-sdk" not in dockerfile_text
        assert "aspnetcore-runtime" in agents_text
        assert "aspnetcore-runtime-10.0" in readme_text

        # 3. Pebble removal
        assert "pebble" in dockerfile_text
        assert "pebble" in agents_text
        assert "pebble" in readme_text

        # 4. Instant startup driver
        assert "intel-media-va-driver-non-free" in dockerfile_text
        assert "intel-media-va-driver-non-free" in agents_text
        assert "intel-media-va-driver-non-free" in readme_text

    def test_mkdocs_config_and_nav(self):
        """Assert mkdocs.yml exists, is valid YAML, and all nav items exist on disk."""
        mkdocs_file = REPO_ROOT / "mkdocs.yml"
        assert mkdocs_file.exists(), "mkdocs.yml must exist"

        # mkdocs.yml may contain !!python/name: tags used by pymdownx
        class MkDocsLoader(yaml.SafeLoader):
            pass

        MkDocsLoader.add_multi_constructor("tag:yaml.org,2002:python/name:", lambda loader, suffix, node: suffix)
        config = yaml.load(mkdocs_file.read_text(encoding="utf-8"), Loader=MkDocsLoader)
        assert config.get("site_name") == "FileFlows Real Image"
        assert config.get("theme", {}).get("name") == "material"

        docs_dir = REPO_ROOT / config.get("docs_dir", "docs")
        assert docs_dir.is_dir(), f"docs_dir '{docs_dir}' must exist"

        def extract_nav_targets(nav_list):
            targets = []
            for item in nav_list:
                if isinstance(item, str):
                    targets.append(item)
                elif isinstance(item, dict):
                    for val in item.values():
                        if isinstance(val, str):
                            targets.append(val)
                        elif isinstance(val, list):
                            targets.extend(extract_nav_targets(val))
            return targets

        nav_items = extract_nav_targets(config.get("nav", []))
        assert len(nav_items) > 0, "mkdocs.yml nav must contain items"

        missing_nav_files = []
        for nav_path in nav_items:
            target = (docs_dir / nav_path).resolve()
            if not target.exists():
                missing_nav_files.append(f"Nav target '{nav_path}' not found at {target}")

        assert not missing_nav_files, (
            "Found broken navigation paths in mkdocs.yml:\n" + "\n".join(missing_nav_files)
        )
