import json
import os
import unittest

from stand_helpers import StandCase, ns, sample_theme
from engine import StandError, theme


class ActiveTest(StandCase):
    def apply_one(self):
        theme.run(ns("create", "one", file=str(self.draft(sample_theme("One")))))
        theme.run(ns("apply", "one"))

    def test_active_returns_the_applied_theme(self):
        self.apply_one()
        data = theme.run(ns("active")).data
        self.assertEqual(data["name"], "one")
        self.assertEqual(data["label"], "Holocron")
        self.assertEqual(data["verbs"][0], "Verb 0")
        self.assertEqual(len(data["announcements"]), 20)
        self.assertEqual(data["names"][0], "Name 0")

    def test_active_needs_no_data_folder(self):
        self.apply_one()
        del os.environ["CLAUDE_PLUGIN_DATA"]
        self.assertEqual(theme.run(ns("active")).data["name"], "one")

    def test_active_without_a_theme_is_an_error(self):
        with self.assertRaises(StandError):
            theme.run(ns("active"))

    def test_active_ignores_a_foreign_tips_file(self):
        (self.config / "settings.json").write_text(
            json.dumps({"spinnerTipsOverride": {"tipsFile": "/tmp/other/tips.json", "label": "x"}}),
            encoding="utf-8")
        with self.assertRaises(StandError):
            theme.run(ns("active"))

    def test_active_drops_non_string_entries(self):
        self.apply_one()
        names_file = self.data / "active" / "theme" / "one" / "names.json"
        names_file.write_text(json.dumps(["Ann", 5, "", None, "Bo"]), encoding="utf-8")
        self.assertEqual(theme.run(ns("active")).data["names"], ["Ann", "Bo"])

    def test_cli_prints_json_and_fails_cleanly_when_none(self):
        r = self.run_cli("theme", "active", "--json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("No Stand theme is active", r.stderr)
        self.apply_one()
        r = self.run_cli("theme", "active", "--json")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)["data"]["name"], "one")


if __name__ == "__main__":
    unittest.main()
