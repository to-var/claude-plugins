import json
import re
import unittest

from tovar_helpers import REPO

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
HEADING = re.compile(r"^## (tovar-[a-z]+) (\d+\.\d+\.\d+) \((\d{4}-\d{2}-\d{2})\)$", re.M)
PLUGINS = sorted(p.parent.parent for p in REPO.glob("*/.claude-plugin/plugin.json"))


def manifest(folder):
    return json.loads((folder / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))


class ReleaseTest(unittest.TestCase):
    def test_every_plugin_has_a_semver_version(self):
        self.assertTrue(PLUGINS)
        for folder in PLUGINS:
            self.assertRegex(manifest(folder)["version"], SEMVER, folder.name)

    def test_the_changelog_leads_with_each_plugins_current_version(self):
        text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        newest = {}
        for name, version, _ in HEADING.findall(text):
            newest.setdefault(name, version)
        for folder in PLUGINS:
            info = manifest(folder)
            self.assertEqual(newest.get(info["name"]), info["version"],
                             f"CHANGELOG.md needs '## {info['name']} {info['version']} (date)' as its newest entry")

    def test_every_marketplace_plugin_matches_a_folder(self):
        market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(p["name"] for p in market["plugins"]), sorted(f.name for f in PLUGINS))

    def test_the_versioning_rule_is_loaded_by_claude_md(self):
        self.assertIn("## Versioning and releases", (REPO / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertIn("@AGENTS.md", (REPO / "CLAUDE.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
