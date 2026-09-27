import json
import unittest

from helpers import REPO


class ScaffoldTest(unittest.TestCase):
    def test_plugin_manifest_is_valid(self):
        manifest = json.loads(
            (REPO / "setup" / "tovar-setup" / ".claude-plugin" / "plugin.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "tovar-setup")
        self.assertIn("repository", manifest)

    def test_setup_json_has_empty_groups(self):
        setup = json.loads(
            (REPO / "setup" / "tovar-setup" / "setup.json").read_text(encoding="utf-8")
        )
        self.assertEqual(setup, {
            "marketplaces": [], "plugins": [], "settings": {}, "statusline": None,
            "claude_md": {"text": ""},
        })

    def test_marketplace_lists_tovar_setup(self):
        market = json.loads(
            (REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        entry = next(p for p in market["plugins"] if p["name"] == "tovar-setup")
        self.assertEqual(entry["source"], "./setup/tovar-setup")


if __name__ == "__main__":
    unittest.main()
