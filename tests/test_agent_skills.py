"""Test suite asserting integrity of agent skills, Claude subagents, and editor configurations."""

import json
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
CLAUDE_DIR = REPO_ROOT / ".claude"
CURSOR_DIR = REPO_ROOT / ".cursor"
ZED_DIR = REPO_ROOT / ".zed"


class TestAgentSkillsAndTooling:
    """Assertions ensuring all agent skills and contributor directives conform to project standards."""

    def _parse_frontmatter(self, file_path: Path) -> dict:
        content = file_path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return {}
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return yaml.safe_load(parts[1]) or {}
        return {}

    def test_all_skills_have_valid_frontmatter(self):
        """Assert every skill under .agents/skills has a SKILL.md with valid name and description."""
        assert AGENTS_SKILLS_DIR.is_dir(), ".agents/skills directory must exist"
        skill_dirs = [d for d in AGENTS_SKILLS_DIR.iterdir() if d.is_dir()]
        assert len(skill_dirs) >= 6, f"Expected at least 6 agent skills, found {len(skill_dirs)}"

        for sdir in skill_dirs:
            skill_md = sdir / "SKILL.md"
            assert skill_md.exists(), f"Skill directory {sdir.name} missing SKILL.md"
            meta = self._parse_frontmatter(skill_md)
            assert "name" in meta, f"{skill_md} missing 'name' in frontmatter"
            assert "description" in meta, f"{skill_md} missing 'description' in frontmatter"
            assert meta["name"] == sdir.name, (
                f"Frontmatter name '{meta['name']}' does not match directory '{sdir.name}'"
            )
            assert len(meta["description"].strip()) > 10, f"Description in {skill_md} is too short"

    def test_claude_skills_symlink(self):
        """Assert .claude/skills is a valid symlink pointing to .agents/skills."""
        claude_skills = CLAUDE_DIR / "skills"
        assert claude_skills.exists(), ".claude/skills must exist"
        assert claude_skills.is_symlink(), ".claude/skills must be a symlink"
        resolved = claude_skills.resolve()
        assert resolved == AGENTS_SKILLS_DIR.resolve(), (
            f".claude/skills resolves to {resolved}, expected {AGENTS_SKILLS_DIR.resolve()}"
        )

    def test_claude_review_agents(self):
        """Assert review subagents in .claude/agents have valid frontmatter and tool configs."""
        agents_dir = CLAUDE_DIR / "agents"
        assert agents_dir.is_dir(), ".claude/agents must exist"
        agent_files = list(agents_dir.glob("*.md"))
        assert len(agent_files) >= 2, f"Expected at least 2 review agents, found {len(agent_files)}"

        for af in agent_files:
            meta = self._parse_frontmatter(af)
            assert "name" in meta, f"{af.name} missing 'name'"
            assert "description" in meta, f"{af.name} missing 'description'"
            assert "model" in meta, f"{af.name} missing 'model'"
            assert "tools" in meta, f"{af.name} missing 'tools'"

    def test_claude_settings_permissions(self):
        """Assert .claude/settings.json defines safe permissions without open wildcards."""
        settings_file = CLAUDE_DIR / "settings.json"
        assert settings_file.exists()
        data = json.loads(settings_file.read_text(encoding="utf-8"))

        perms = data.get("permissions", {})
        allowed = perms.get("allow", [])
        denied = perms.get("deny", [])

        assert len(allowed) > 0, "No allowed commands configured in .claude/settings.json"
        assert len(denied) > 0, "No denied safety commands configured in .claude/settings.json"

        # Check essential allowed tools
        for tool_prefix in ["Bash(docker", "Bash(make", "Bash(pytest", "Bash(git"]:
            assert any(tool_prefix in cmd for cmd in allowed), f"Missing permission for {tool_prefix}"

        # Check critical deny rules
        for dangerous in ["rm -rf /", "git push --force"]:
            assert any(dangerous in cmd for cmd in denied), f"Missing safety block for {dangerous}"

    def test_cursor_and_windsurf_rules(self):
        """Assert Cursor rules and Windsurf rules exist and reference core directives."""
        cursor_mdc = CURSOR_DIR / "rules" / "fileflows.mdc"
        assert cursor_mdc.exists(), ".cursor/rules/fileflows.mdc must exist"
        meta = self._parse_frontmatter(cursor_mdc)
        assert "description" in meta or "globs" in meta or meta == {}

        cursorrules = REPO_ROOT / ".cursorrules"
        assert cursorrules.exists()
        assert "AGENTS.md" in cursorrules.read_text(encoding="utf-8")

        windsurfrules = REPO_ROOT / ".windsurfrules"
        assert windsurfrules.exists()
        assert "AGENTS.md" in windsurfrules.read_text(encoding="utf-8")

    def test_zed_configuration_and_tasks(self):
        """Assert .zed configurations are valid JSON and tasks map to Makefile targets."""
        zed_settings = ZED_DIR / "settings.json"
        zed_tasks = ZED_DIR / "tasks.json"
        assert zed_settings.exists()
        assert zed_tasks.exists()

        settings_data = json.loads(zed_settings.read_text(encoding="utf-8"))
        assert "languages" in settings_data

        tasks_data = json.loads(zed_tasks.read_text(encoding="utf-8"))
        assert isinstance(tasks_data, list)
        makefile_content = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

        for task in tasks_data:
            assert "label" in task
            assert "command" in task
            cmd = task["command"]
            if cmd.startswith("make "):
                target = cmd.split("make ")[1].strip()
                assert f"{target}:" in makefile_content, f"Zed task target '{target}' missing from Makefile"
