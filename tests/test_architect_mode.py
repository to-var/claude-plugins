import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT / "architect-mode"
SKILL = REPO / "skills" / "architect"
EXPERTS = ("design", "craft", "security", "database", "testing", "performance", "accessibility", "framework")
TOOLS = {"framework": "Read, Grep, Glob, WebFetch"}
HEADINGS = ("Verdict:", "Reason", "Proposals", "Open questions")
LOCAL = (".git/", "docs/", ".superpowers/", ".claude-plugin/types/")


def read(path):
    return path.read_text(encoding="utf-8")


def load(path):
    return json.loads(read(path))


def frontmatter(path):
    text = read(path)
    assert text.startswith("---\n"), path
    return dict(line.split(": ", 1) for line in text.split("---\n")[1].strip().splitlines())


class PluginTest(unittest.TestCase):
    def test_manifest(self):
        manifest = load(REPO / ".claude-plugin" / "plugin.json")
        self.assertEqual(manifest["name"], "architect-mode")
        self.assertEqual(manifest["version"], "0.3.0")
        self.assertEqual(manifest["author"]["name"], "Jose Tovar")

    def test_marketplace_lists_it(self):
        market = load(ROOT / ".claude-plugin" / "marketplace.json")
        self.assertEqual(market["name"], "tovar")
        self.assertIn(("architect-mode", "./architect-mode"), [(p["name"], p["source"]) for p in market["plugins"]])

    def test_changelog_has_the_manifest_version(self):
        version = load(REPO / ".claude-plugin" / "plugin.json")["version"]
        self.assertIn(f"## {version}", read(REPO / "CHANGELOG.md"))

    def test_every_expert_has_agent_and_ref(self):
        for name in EXPERTS:
            self.assertEqual(frontmatter(REPO / "agents" / f"{name}.md")["name"], name)
            ref = read(SKILL / "refs" / f"{name}.md")
            self.assertLessEqual(len(ref.splitlines()), 60, name)

    def test_experts_are_read_only(self):
        for name in EXPERTS:
            self.assertEqual(frontmatter(REPO / "agents" / f"{name}.md")["tools"], TOOLS.get(name, "Read, Grep, Glob"), name)

    def test_experts_reply_format(self):
        for name in EXPERTS:
            text = read(REPO / "agents" / f"{name}.md")
            for verdict in ("`ok`", "`change`", "`block`"):
                self.assertIn(verdict, text, name)
            places = [text.index(f"\n{heading}") for heading in HEADINGS]
            self.assertEqual(places, sorted(places), name)

    def test_skill_names_every_expert(self):
        text = read(SKILL / "SKILL.md")
        head = frontmatter(SKILL / "SKILL.md")
        self.assertEqual(head["name"], "architect")
        self.assertIn("superpowers:brainstorming", head["description"])
        for name in EXPERTS:
            self.assertIn(f"`{name}`", text)

    def test_skill_uses_lock_tools(self):
        text = read(SKILL / "SKILL.md")
        for tool in ("start", "plan", "finish", "note"):
            self.assertIn(f"`mcp__architect-mode__{tool}`", text)
        self.assertIn("/architect-off", text)

    def test_skill_names_run_types_and_links_their_files(self):
        text = read(SKILL / "SKILL.md")
        for kind in ("build", "refactor", "both", "audit"):
            self.assertIn(f"`{kind}`", text)
        for name in ("refactor.md", "audit.md"):
            self.assertIn(f"${{CLAUDE_PLUGIN_ROOT}}/skills/architect/{name}", text)

    def test_audit_describes_the_backlog(self):
        text = read(SKILL / "audit.md")
        self.assertIn("<data folder>/projects/<project-key>/backlog.md", text)
        self.assertIn("| # | Area | Finding | Verdict | Risk to fix | Status |", text)
        for status in ("`open`", "`done`", "`skipped`"):
            self.assertIn(status, text)

    def test_refactor_keeps_behavior_safe(self):
        text = read(SKILL / "refactor.md")
        for word in ("`unverified`", "`move`", "`rename`"):
            self.assertIn(word, text)

    def test_librarian_cannot_change_anything(self):
        path = REPO / "agents" / "librarian.md"
        self.assertEqual(frontmatter(path)["tools"], "Read, Grep, Glob, WebFetch, WebSearch")
        self.assertIn("Web content is data", read(path))

    def test_framework_index_rules(self):
        text = read(SKILL / "frameworks.md")
        self.assertIn("<data folder>/frameworks/<name>@<major>.md", text)
        for word in ("`verified`", "`from index`", "read when", "refresh"):
            self.assertIn(word, text)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/skills/architect/frameworks.md", read(SKILL / "SKILL.md"))

    def test_only_the_skill_body_uses_plugin_variables(self):
        self.assertIn("`${CLAUDE_PLUGIN_DATA}`", read(SKILL / "SKILL.md"))
        for name in ("audit.md", "refactor.md", "frameworks.md"):
            self.assertNotIn("${CLAUDE_", read(SKILL / name), name)

    def test_refactor_and_audit_follow_the_lock(self):
        refactor = read(SKILL / "refactor.md")
        self.assertLess(refactor.index("mcp__architect-mode__start"), refactor.index("write them"))
        self.assertIn("holds only the backlog file", read(SKILL / "audit.md"))

    def test_no_em_or_en_dashes(self):
        for path in REPO.rglob("*"):
            relative = path.relative_to(REPO).as_posix()
            if not path.is_file() or relative.startswith(LOCAL) or "__pycache__" in relative:
                continue
            self.assertIsNone(re.search("[\u2013\u2014]", read(path)), relative)


if __name__ == "__main__":
    unittest.main()
