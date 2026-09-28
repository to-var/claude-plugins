import json
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import REPO, make_fake_claude, make_setup_root, run_setup


class ScaffoldTest(unittest.TestCase):
    def test_plugin_manifest_is_valid(self):
        manifest = json.loads(
            (REPO / "setup" / "tovar-setup" / ".claude-plugin" / "plugin.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "tovar-setup")
        self.assertIn("repository", manifest)

    def test_setup_json_has_the_expected_shape(self):
        # The repo's setup.json holds Jose's real captured data, filled in by
        # /tovar-setup:capture, so its groups are not asserted empty here.
        setup = json.loads(
            (REPO / "setup" / "tovar-setup" / "setup.json").read_text(encoding="utf-8")
        )
        self.assertEqual(set(setup.keys()),
                          {"marketplaces", "plugins", "settings", "statusline", "claude_md"})
        self.assertIsInstance(setup["marketplaces"], list)
        self.assertIsInstance(setup["plugins"], list)
        self.assertIsInstance(setup["settings"], dict)
        self.assertIsInstance(setup["claude_md"], dict)
        self.assertIn("text", setup["claude_md"])

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

    def test_apply_claude_md_does_not_lose_content_with_lone_marker(self):
        # Test for bug: unbalanced markers causing silent data loss
        # Scenario: user has a lone unclosed MD_BEGIN in their file, then apply-claude-md twice
        content_before_marker = "# My custom rules\n\nImportant stuff here.\n"
        lone_marker = "<!-- tovar-setup:begin -->"
        content_after_marker = "More important content.\n"

        # First state: file with lone unclosed marker and real content after
        self.md.write_text(content_before_marker + lone_marker + "\n" + content_after_marker, encoding="utf-8")
        self.save_setup("Block one.")
        r = self.run_cmd("apply-claude-md")
        self.assertEqual(r.returncode, 0, r.stderr)
        after_first_apply = self.md.read_text(encoding="utf-8")

        # After first apply, should have appended (since only one marker, not both)
        self.assertIn(content_before_marker, after_first_apply)
        self.assertIn(content_after_marker, after_first_apply)
        self.assertIn("Block one.", after_first_apply)

        # Second apply with different text
        self.save_setup("Block two.")
        r = self.run_cmd("apply-claude-md")
        self.assertEqual(r.returncode, 0, r.stderr)
        after_second_apply = self.md.read_text(encoding="utf-8")

        # After second apply, all original content must still be there
        # (This was the bug: content_after_marker was being silently deleted)
        # With unbalanced markers, we append again, so both blocks are present
        self.assertIn(content_before_marker, after_second_apply)
        self.assertIn(content_after_marker, after_second_apply)
        self.assertIn("Block one.", after_second_apply)
        self.assertIn("Block two.", after_second_apply)

    def test_save_md_rejects_invalid_json(self):
        r = self.run_cmd("save-md", stdin="not valid json")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("valid JSON", r.stderr)
        # Verify setup.json was not modified
        setup = json.loads((self.plugin / "setup.json").read_text(encoding="utf-8"))
        self.assertEqual(setup["claude_md"]["text"], "")

    def test_save_md_rejects_json_array(self):
        r = self.run_cmd("save-md", stdin=json.dumps(["text"]))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('{"text":', r.stderr)
        setup = json.loads((self.plugin / "setup.json").read_text(encoding="utf-8"))
        self.assertEqual(setup["claude_md"]["text"], "")

    def test_save_md_rejects_object_without_text_key(self):
        r = self.run_cmd("save-md", stdin=json.dumps({"foo": "bar"}))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('{"text":', r.stderr)
        setup = json.loads((self.plugin / "setup.json").read_text(encoding="utf-8"))
        self.assertEqual(setup["claude_md"]["text"], "")

    def test_save_md_rejects_text_with_wrong_type(self):
        r = self.run_cmd("save-md", stdin=json.dumps({"text": 123}))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('{"text":', r.stderr)
        setup = json.loads((self.plugin / "setup.json").read_text(encoding="utf-8"))
        self.assertEqual(setup["claude_md"]["text"], "")

    def test_save_md_rejects_text_containing_managed_block_marker(self):
        r = self.run_cmd(
            "save-md",
            stdin=json.dumps({"text": "some text <!-- tovar-setup:begin --> more text"}),
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("managed block", r.stderr)
        setup = json.loads((self.plugin / "setup.json").read_text(encoding="utf-8"))
        self.assertEqual(setup["claude_md"]["text"], "")


class PluginsGroupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.plugin = make_setup_root(self.tmp.name)
        self.cfg = Path(self.tmp.name) / "cfg"
        self.cfg.mkdir()
        self.settings = self.cfg / "settings.json"
        self.log = Path(self.tmp.name) / "calls.log"
        self.fake_claude = make_fake_claude(self.tmp.name)

    def save_settings(self, data):
        self.settings.write_text(json.dumps(data), encoding="utf-8")

    def save_setup(self, marketplaces, plugins):
        (self.plugin / "setup.json").write_text(json.dumps({
            "marketplaces": marketplaces, "plugins": plugins, "settings": {},
            "statusline": None, "claude_md": {"text": ""},
        }), encoding="utf-8")

    def run_cmd(self, cmd, stdin="", fail=""):
        return run_setup(self.plugin, cmd, stdin=stdin, cfg=self.cfg, env={
            "FAKE_CLAUDE_LOG": str(self.log),
            "FAKE_CLAUDE_FAIL": fail,
            "TOVAR_SETUP_CLAUDE_CMD_JSON": json.dumps([sys.executable, str(self.fake_claude)]),
        })

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(l) for l in self.log.read_text(encoding="utf-8").splitlines()]

    def test_plan_reports_missing_marketplace_and_plugin(self):
        self.save_settings({})
        self.save_setup([{"name": "tovar", "repo": "to-var/claude-plugins"}], ["tovar-themes-pop@tovar"])
        r = self.run_cmd("plan-plugins")
        self.assertEqual(json.loads(r.stdout), {
            "status": "differs",
            "marketplaces": [{"name": "tovar", "repo": "to-var/claude-plugins"}],
            "plugins": ["tovar-themes-pop@tovar"],
        })

    def test_plan_skips_already_installed(self):
        self.save_settings({
            "extraKnownMarketplaces": {"tovar": {"source": {"source": "github", "repo": "to-var/claude-plugins"}}},
            "enabledPlugins": {"tovar-themes-pop@tovar": True},
        })
        self.save_setup([{"name": "tovar", "repo": "to-var/claude-plugins"}], ["tovar-themes-pop@tovar"])
        r = self.run_cmd("plan-plugins")
        self.assertEqual(json.loads(r.stdout)["status"], "match")

    def test_apply_calls_claude_for_each_missing_item(self):
        self.save_settings({})
        self.save_setup([{"name": "tovar", "repo": "to-var/claude-plugins"}],
                         ["tovar-themes-pop@tovar", "tovar-output-styles@tovar"])
        r = self.run_cmd("apply-plugins")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.calls(), [
            ["plugin", "marketplace", "add", "to-var/claude-plugins"],
            ["plugin", "install", "tovar-themes-pop@tovar"],
            ["plugin", "install", "tovar-output-styles@tovar"],
        ])
        self.assertIn("installed tovar-themes-pop@tovar", r.stdout)

    def test_apply_reports_one_failure_but_continues(self):
        self.save_settings({})
        self.save_setup([], ["a@tovar", "b@tovar"])
        r = self.run_cmd("apply-plugins", fail="a@tovar")
        self.assertIn("error installing a@tovar", r.stdout)
        self.assertIn("installed b@tovar", r.stdout)

    def test_apply_is_noop_when_nothing_captured(self):
        self.save_settings({})
        self.save_setup([], [])
        r = self.run_cmd("apply-plugins")
        self.assertIn("nothing to do", r.stdout)
        self.assertEqual(self.calls(), [])

    def test_read_state_lists_local_marketplaces_and_plugins(self):
        self.save_settings({
            "extraKnownMarketplaces": {"tovar": {"source": {"source": "github", "repo": "to-var/claude-plugins"}}},
            "enabledPlugins": {"tovar-themes-pop@tovar": True, "tovar-themes-pokemon@tovar": False},
            "model": "sonnet",
        })
        r = self.run_cmd("read-state")
        data = json.loads(r.stdout)
        self.assertEqual(data["plugins"], ["tovar-themes-pop@tovar"])
        self.assertEqual(data["settings"], {"model": "sonnet"})

    def test_save_state_writes_approved_groups_only(self):
        self.save_setup([], [])
        approved = {"plugins": ["tovar-themes-pop@tovar"], "settings": {"model": "sonnet", "secret": "x"}}
        r = self.run_cmd("save-state", stdin=json.dumps(approved))
        self.assertEqual(r.returncode, 0, r.stderr)
        setup = json.loads((self.plugin / "setup.json").read_text(encoding="utf-8"))
        self.assertEqual(setup["plugins"], ["tovar-themes-pop@tovar"])
        self.assertEqual(setup["settings"], {"model": "sonnet"})
        self.assertEqual(setup["marketplaces"], [])

    def test_save_state_rejects_marketplaces_dict_instead_of_list(self):
        self.save_setup([], [])
        before = (self.plugin / "setup.json").read_text(encoding="utf-8")
        approved = {"marketplaces": {"tovar": {"repo": "to-var/claude-plugins"}}}
        r = self.run_cmd("save-state", stdin=json.dumps(approved))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("marketplaces", r.stderr)
        self.assertEqual((self.plugin / "setup.json").read_text(encoding="utf-8"), before)

    def test_save_state_rejects_plugins_with_non_string_item(self):
        self.save_setup([], [])
        before = (self.plugin / "setup.json").read_text(encoding="utf-8")
        approved = {"plugins": ["tovar-themes-pop@tovar", 123]}
        r = self.run_cmd("save-state", stdin=json.dumps(approved))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("plugins", r.stderr)
        self.assertEqual((self.plugin / "setup.json").read_text(encoding="utf-8"), before)

    def test_save_state_rejects_marketplace_missing_repo(self):
        self.save_setup([], [])
        before = (self.plugin / "setup.json").read_text(encoding="utf-8")
        approved = {"marketplaces": [{"name": "tovar"}]}
        r = self.run_cmd("save-state", stdin=json.dumps(approved))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("marketplaces", r.stderr)
        self.assertEqual((self.plugin / "setup.json").read_text(encoding="utf-8"), before)

    def test_apply_continues_on_oserror(self):
        self.save_settings({})
        self.save_setup([], ["a@tovar", "b@tovar", "c@tovar"])
        # Point to a non-existent binary to trigger OSError
        bad_env = {
            "FAKE_CLAUDE_LOG": str(self.log),
            "FAKE_CLAUDE_FAIL": "",
            "TOVAR_SETUP_CLAUDE_CMD_JSON": json.dumps(["/no/such/binary"]),
        }
        r = run_setup(self.plugin, "apply-plugins", cfg=self.cfg, env=bad_env)
        # Should succeed (not crash) even though command doesn't exist
        self.assertEqual(r.returncode, 0, r.stderr)
        # Should report error for non-existent binary
        self.assertIn("error installing a@tovar", r.stdout)
        # Should still attempt remaining items despite OSError on first
        self.assertIn("error installing b@tovar", r.stdout)
        self.assertIn("error installing c@tovar", r.stdout)


class IntegrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.plugin = make_setup_root(self.tmp.name)
        self.cfg = Path(self.tmp.name) / "cfg"
        self.cfg.mkdir()
        self.log = Path(self.tmp.name) / "calls.log"
        self.fake_claude = make_fake_claude(self.tmp.name)
        (self.plugin / "setup.json").write_text(json.dumps({
            "marketplaces": [{"name": "tovar", "repo": "to-var/claude-plugins"}],
            "plugins": ["tovar-themes-pop@tovar"],
            "settings": {"model": "sonnet", "outputStyle": "ELI5"},
            "statusline": {"type": "command", "command": "run-hud"},
            "claude_md": {"text": "## Style\nNo dashes."},
        }), encoding="utf-8")

    def run_cmd(self, cmd):
        return run_setup(self.plugin, cmd, cfg=self.cfg, env={
            "FAKE_CLAUDE_LOG": str(self.log),
            "TOVAR_SETUP_CLAUDE_CMD_JSON": json.dumps([sys.executable, str(self.fake_claude)]),
        })

    def apply_all(self):
        return [self.run_cmd(c) for c in
                ("apply-plugins", "apply-settings", "apply-statusline", "apply-claude-md")]

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(l) for l in self.log.read_text(encoding="utf-8").splitlines()]

    def test_fresh_machine_gets_everything(self):
        for r in self.apply_all():
            self.assertEqual(r.returncode, 0, r.stderr)
        settings = json.loads((self.cfg / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["model"], "sonnet")
        self.assertEqual(settings["outputStyle"], "ELI5")
        self.assertEqual(settings["statusLine"], {"type": "command", "command": "run-hud"})
        self.assertIn("No dashes.", (self.cfg / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertEqual(self.calls(), [
            ["plugin", "marketplace", "add", "to-var/claude-plugins"],
            ["plugin", "install", "tovar-themes-pop@tovar"],
        ])

    def test_settings_statusline_and_claude_md_are_noop_on_rerun(self):
        self.apply_all()
        for cmd in ("apply-settings", "apply-statusline", "apply-claude-md"):
            r = self.run_cmd(cmd)
            self.assertIn("nothing to do", r.stdout, r.stdout)


if __name__ == "__main__":
    unittest.main()
