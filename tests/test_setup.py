import json
import tempfile
import unittest
from pathlib import Path

from helpers import REPO, make_setup_root, run_setup


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


class SettingsGroupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.plugin = make_setup_root(self.tmp.name)
        self.cfg = Path(self.tmp.name) / "cfg"
        self.cfg.mkdir()
        self.settings = self.cfg / "settings.json"

    def save_settings(self, data):
        self.settings.write_text(json.dumps(data), encoding="utf-8")

    def load_settings(self):
        return json.loads(self.settings.read_text(encoding="utf-8"))

    def save_setup(self, settings):
        (self.plugin / "setup.json").write_text(json.dumps({
            "marketplaces": [], "plugins": [], "settings": settings,
            "statusline": None, "claude_md": {"text": ""},
        }), encoding="utf-8")

    def run_cmd(self, cmd, stdin=""):
        return run_setup(self.plugin, cmd, stdin=stdin, cfg=self.cfg)

    def test_plan_settings_is_empty_when_not_captured(self):
        self.save_settings({"model": "sonnet"})
        r = self.run_cmd("plan-settings")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), {"status": "empty"})

    def test_plan_settings_reports_changes(self):
        self.save_settings({"model": "haiku"})
        self.save_setup({"model": "sonnet"})
        r = self.run_cmd("plan-settings")
        self.assertEqual(json.loads(r.stdout), {"status": "differs", "changes": {"model": "sonnet"}})

    def test_apply_settings_writes_only_captured_keys(self):
        self.save_settings({"model": "haiku", "tui": "compact"})
        self.save_setup({"model": "sonnet"})
        r = self.run_cmd("apply-settings")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("settings: set model = 'sonnet'", r.stdout)
        s = self.load_settings()
        self.assertEqual(s["model"], "sonnet")
        self.assertEqual(s["tui"], "compact")

    def test_apply_settings_second_run_is_noop(self):
        self.save_settings({"model": "haiku"})
        self.save_setup({"model": "sonnet"})
        self.run_cmd("apply-settings")
        r = self.run_cmd("apply-settings")
        self.assertIn("already matches", r.stdout)

    def test_apply_settings_backs_up_first(self):
        self.save_settings({"model": "haiku"})
        self.save_setup({"model": "sonnet"})
        self.run_cmd("apply-settings")
        backups = list((self.cfg / "tovar-setup").glob("settings.json.backup.*"))
        self.assertEqual(len(backups), 1)

    def test_missing_settings_file_is_created(self):
        self.save_setup({"model": "sonnet"})
        r = self.run_cmd("apply-settings")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.load_settings(), {"model": "sonnet"})

    def test_invalid_settings_json_stops_with_error(self):
        self.settings.write_text("{ not json", encoding="utf-8")
        self.save_setup({"model": "sonnet"})
        r = self.run_cmd("apply-settings")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not valid JSON", r.stderr)
        self.assertEqual(self.settings.read_text(encoding="utf-8"), "{ not json")


class StatuslineGroupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.plugin = make_setup_root(self.tmp.name)
        self.cfg = Path(self.tmp.name) / "cfg"
        self.cfg.mkdir()
        self.settings = self.cfg / "settings.json"

    def save_settings(self, data):
        self.settings.write_text(json.dumps(data), encoding="utf-8")

    def load_settings(self):
        return json.loads(self.settings.read_text(encoding="utf-8"))

    def save_setup(self, statusline):
        (self.plugin / "setup.json").write_text(json.dumps({
            "marketplaces": [], "plugins": [], "settings": {},
            "statusline": statusline, "claude_md": {"text": ""},
        }), encoding="utf-8")

    def run_cmd(self, cmd):
        return run_setup(self.plugin, cmd, cfg=self.cfg)

    def test_plan_statusline_is_empty_when_not_captured(self):
        self.save_settings({})
        r = self.run_cmd("plan-statusline")
        self.assertEqual(json.loads(r.stdout), {"status": "empty"})

    def test_plan_statusline_reports_differs(self):
        self.save_settings({"statusLine": {"type": "command", "command": "old"}})
        self.save_setup({"type": "command", "command": "new"})
        r = self.run_cmd("plan-statusline")
        self.assertEqual(json.loads(r.stdout),
                          {"status": "differs", "value": {"type": "command", "command": "new"}})

    def test_plan_statusline_reports_match(self):
        self.save_settings({"statusLine": {"type": "command", "command": "same"}})
        self.save_setup({"type": "command", "command": "same"})
        r = self.run_cmd("plan-statusline")
        self.assertEqual(json.loads(r.stdout),
                          {"status": "match", "value": {"type": "command", "command": "same"}})

    def test_apply_statusline_writes_it_and_second_run_is_noop(self):
        self.save_settings({"theme": "dark"})
        self.save_setup({"type": "command", "command": "new"})
        r = self.run_cmd("apply-statusline")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("updated", r.stdout)
        s = self.load_settings()
        self.assertEqual(s["statusLine"], {"type": "command", "command": "new"})
        self.assertEqual(s["theme"], "dark")
        r = self.run_cmd("apply-statusline")
        self.assertIn("already matches", r.stdout)


class ClaudeMdGroupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.plugin = make_setup_root(self.tmp.name)
        self.cfg = Path(self.tmp.name) / "cfg"
        self.cfg.mkdir()
        self.md = self.cfg / "CLAUDE.md"

    def save_setup(self, text):
        (self.plugin / "setup.json").write_text(json.dumps({
            "marketplaces": [], "plugins": [], "settings": {}, "statusline": None,
            "claude_md": {"text": text},
        }), encoding="utf-8")

    def run_cmd(self, cmd, stdin=""):
        return run_setup(self.plugin, cmd, stdin=stdin, cfg=self.cfg)

    def test_read_md_splits_into_sections(self):
        self.md.write_text(
            "Intro line.\n\n## Style\nUse plain words.\n\n## Attribution\nNo bylines.\n",
            encoding="utf-8",
        )
        r = self.run_cmd("read-md")
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertTrue(data["exists"])
        self.assertEqual([s["heading"] for s in data["sections"]], [None, "Style", "Attribution"])
        self.assertEqual(data["sections"][1]["text"], "Use plain words.")

    def test_read_md_missing_file(self):
        r = self.run_cmd("read-md")
        self.assertEqual(json.loads(r.stdout), {"exists": False, "sections": []})

    def test_save_md_writes_setup_json(self):
        r = self.run_cmd("save-md", stdin=json.dumps({"text": "No em dashes."}))
        self.assertEqual(r.returncode, 0, r.stderr)
        setup = json.loads((self.plugin / "setup.json").read_text(encoding="utf-8"))
        self.assertEqual(setup["claude_md"]["text"], "No em dashes.")

    def test_apply_claude_md_creates_file(self):
        self.save_setup("No em dashes.")
        r = self.run_cmd("apply-claude-md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("No em dashes.", self.md.read_text(encoding="utf-8"))

    def test_apply_claude_md_keeps_other_lines_and_rerun_is_idempotent(self):
        self.md.write_text("# My rules\n\nKeep this line.\n", encoding="utf-8")
        self.save_setup("No em dashes.")
        self.run_cmd("apply-claude-md")
        first = self.md.read_text(encoding="utf-8")
        r = self.run_cmd("apply-claude-md")
        self.assertIn("already matches", r.stdout)
        self.assertEqual(self.md.read_text(encoding="utf-8"), first)
        self.assertIn("Keep this line.", first)

    def test_apply_claude_md_replaces_block_on_change(self):
        self.save_setup("Version one.")
        self.run_cmd("apply-claude-md")
        self.save_setup("Version two.")
        self.run_cmd("apply-claude-md")
        text = self.md.read_text(encoding="utf-8")
        self.assertIn("Version two.", text)
        self.assertNotIn("Version one.", text)

    def test_apply_claude_md_backs_up_existing_file(self):
        self.md.write_text("# My rules\n", encoding="utf-8")
        self.save_setup("No em dashes.")
        self.run_cmd("apply-claude-md")
        backups = list((self.cfg / "tovar-setup").glob("CLAUDE.md.backup.*"))
        self.assertEqual(len(backups), 1)

    def test_apply_claude_md_empty_text_is_noop(self):
        self.save_setup("")
        r = self.run_cmd("apply-claude-md")
        self.assertIn("nothing to do", r.stdout)
        self.assertFalse(self.md.exists())


if __name__ == "__main__":
    unittest.main()
