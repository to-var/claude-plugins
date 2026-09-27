import json
import os
import tempfile
import unittest

from helpers import content, make_root, run_tools


class ToolsTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = make_root(self.tmp.name)

    def plugin(self, theme):
        return self.root / "themes" / f"tovar-themes-{theme}"

    def theme_json(self, theme):
        return json.loads((self.plugin(theme) / "theme.json").read_text(encoding="utf-8"))

    def market(self):
        return json.loads(
            (self.root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )


class NewThemeTest(ToolsTestCase):
    def test_new_builds_plugin_from_template(self):
        r = run_tools(self.root, "new", "star-wars", "Star Wars")
        self.assertEqual(r.returncode, 0, r.stderr)
        plugin = self.plugin("star-wars")
        manifest = json.loads(
            (plugin / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "tovar-themes-star-wars")
        self.assertIn("Star Wars", (plugin / "commands" / "on.md").read_text(encoding="utf-8"))
        for f in plugin.rglob("*"):
            if f.is_file():
                self.assertNotIn("{{", f.read_text(encoding="utf-8"), f)

    def test_new_writes_blank_content_with_tips(self):
        run_tools(self.root, "new", "star-wars", "Star Wars")
        c = self.theme_json("star-wars")
        self.assertEqual(c["display"], "Star Wars")
        self.assertIn("_todo", c)
        self.assertEqual(c["verbs"], [])
        self.assertEqual(c["names"], [])
        self.assertEqual(len(c["tips"]), 5)
        self.assertTrue(any("/tovar-themes-star-wars:off" in t for t in c["tips"]))

    def test_new_escapes_display_name(self):
        display = 'The "Office": Reboot'
        r = run_tools(self.root, "new", "office", display)
        self.assertEqual(r.returncode, 0, r.stderr)
        plugin = self.plugin("office")
        manifest = json.loads(
            (plugin / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertIn(display, manifest["description"])
        for cmd in ("on.md", "off.md"):
            lines = (plugin / "commands" / cmd).read_text(encoding="utf-8").splitlines()
            line = next(l for l in lines if l.startswith("description: "))
            self.assertIn(display, json.loads(line[len("description: "):]))

    def test_new_default_display_name(self):
        run_tools(self.root, "new", "star-wars")
        self.assertEqual(self.theme_json("star-wars")["display"], "Star Wars")

    def test_new_adds_marketplace_entry(self):
        run_tools(self.root, "new", "star-wars", "Star Wars")
        self.assertEqual(self.market()["plugins"], [{
            "name": "tovar-themes-star-wars",
            "source": "./themes/tovar-themes-star-wars",
            "description": "Star Wars theme for Claude Code: spinner verbs, startup lines, "
                           "tips and subagent names.",
        }])

    def test_new_rejects_bad_names(self):
        for bad in ["Star_Wars", "star wars", "../evil", "-lead", ""]:
            r = run_tools(self.root, "new", bad)
            self.assertNotEqual(r.returncode, 0, bad)
        self.assertEqual(list((self.root / "themes").iterdir()), [])
        self.assertEqual(self.market()["plugins"], [])

    def test_new_refuses_existing_theme(self):
        run_tools(self.root, "new", "pop")
        r = run_tools(self.root, "new", "pop")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("already exists", r.stderr)
        self.assertEqual(len(self.market()["plugins"]), 1)


class SyncTest(ToolsTestCase):
    def test_sync_copies_template_change_and_keeps_content(self):
        run_tools(self.root, "new", "pop", "Pop culture")
        theme_json = self.plugin("pop") / "theme.json"
        theme_json.write_text(
            json.dumps(content("Pop culture", "Trivia", ["Neo"])), encoding="utf-8"
        )
        before = theme_json.read_text(encoding="utf-8")
        readme = self.root / "template" / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8") + "\nNew line for {{DISPLAY}}.\n", encoding="utf-8"
        )

        r = run_tools(self.root, "sync")

        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Synced tovar-themes-pop", r.stdout)
        self.assertIn(
            "New line for Pop culture.",
            (self.plugin("pop") / "README.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(theme_json.read_text(encoding="utf-8"), before)

    def test_sync_ignores_folders_without_prefix(self):
        stray = self.root / "themes" / "notes"
        stray.mkdir()
        r = run_tools(self.root, "sync")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(list(stray.iterdir()), [])


class CheckTest(ToolsTestCase):
    def setUp(self):
        super().setUp()
        self.env = {**os.environ, "TOVAR_THEMES_SKIP_VALIDATE": "1"}
        run_tools(self.root, "new", "pop", "Pop culture")

    def write(self, **overrides):
        c = content("Pop culture", "Trivia", [f"Name {i}" for i in range(100)])
        c.update(overrides)
        (self.plugin("pop") / "theme.json").write_text(json.dumps(c), encoding="utf-8")

    def check(self, *themes):
        return run_tools(self.root, "check", *themes, env=self.env)

    def test_check_passes_full_theme(self):
        self.write()
        r = self.check("pop")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("tovar-themes-pop: OK", r.stdout)

    def test_check_with_no_args_checks_every_theme(self):
        self.write()
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("tovar-themes-pop: OK", r.stdout)

    def test_check_fails_blank_theme(self):
        r = self.check("pop")
        self.assertEqual(r.returncode, 1)
        self.assertIn("_todo", r.stdout)
        self.assertIn("tipsLabel is empty", r.stdout)
        self.assertIn("verbs: needs 40, has 0", r.stdout)
        self.assertIn("names: needs at least 100, has 0", r.stdout)

    def test_check_fails_duplicates_and_too_few_names(self):
        self.write(names=["Neo", "Neo"])
        r = self.check("pop")
        self.assertEqual(r.returncode, 1)
        self.assertIn("names: repeated: Neo", r.stdout)
        self.assertIn("names: needs at least 100, has 2", r.stdout)

    def test_check_fails_empty_items(self):
        self.write(verbs=[""] * 40)
        r = self.check("pop")
        self.assertEqual(r.returncode, 1)
        self.assertIn("verbs: every item must be non-empty text", r.stdout)

    def test_check_unknown_theme(self):
        r = self.check("nope")
        self.assertEqual(r.returncode, 1)
        self.assertIn("tovar-themes-nope: not found", r.stdout)


if __name__ == "__main__":
    unittest.main()
