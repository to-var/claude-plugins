import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import make_root, make_theme

BASE = {
    "theme": "dark",
    "statusLine": {"type": "command", "command": "echo hi"},
    "enabledPlugins": {
        "tovar-themes-alpha@local": True,
        "tovar-themes-beta@local": True,
        "tovar-themes-gamma@elsewhere": False,
        "superpowers@official": True,
    },
}
THEME_KEYS = {"spinnerVerbs", "companyAnnouncements", "spinnerTipsOverride"}


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = make_root(self.tmp.name)
        self.alpha = make_theme(root, "alpha", "Alpha", "Alphadex", ["Neo", "Marty McFly"])
        self.beta = make_theme(root, "beta", "Béta", "Betadex", ["Yoda"])
        self.cfg = Path(self.tmp.name) / "cfg"
        self.cfg.mkdir()
        self.settings = self.cfg / "settings.json"
        self.save(BASE)

    def save(self, data):
        self.settings.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def load(self):
        return json.loads(self.settings.read_text(encoding="utf-8"))

    def engine(self, plugin, cmd, stdin=""):
        return subprocess.run(
            [sys.executable, str(plugin / "scripts" / "theme.py"), cmd],
            input=stdin, capture_output=True, text=True,
            env={**os.environ, "CLAUDE_CONFIG_DIR": str(self.cfg)},
        )

    def backups(self, theme):
        return sorted((self.cfg / "tovar-themes" / theme).glob("settings.backup.*.json"))

    # --- on ---

    def test_on_writes_theme_values(self):
        r = self.engine(self.alpha, "on")
        self.assertEqual(r.returncode, 0, r.stderr)
        s = self.load()
        self.assertEqual(s["spinnerVerbs"]["mode"], "replace")
        self.assertEqual(s["spinnerVerbs"]["verbs"][0], "Alpha verb 0")
        self.assertEqual(len(s["companyAnnouncements"]), 20)
        tips = s["spinnerTipsOverride"]
        self.assertEqual(tips["label"], "Alphadex")
        self.assertEqual(
            json.loads(Path(tips["tipsFile"]).read_text(encoding="utf-8"))[0], "Alpha tip 0"
        )
        self.assertEqual(len(self.backups("alpha")), 1)

    def test_on_turns_off_other_themes_only(self):
        r = self.engine(self.alpha, "on")
        self.assertEqual(self.load()["enabledPlugins"], {
            "tovar-themes-alpha@local": True,
            "tovar-themes-beta@local": False,
            "tovar-themes-gamma@elsewhere": False,
            "superpowers@official": True,
        })
        self.assertIn("Turned off tovar-themes-beta@local", r.stdout)
        self.assertNotIn("gamma", r.stdout)

    def test_on_keeps_every_other_key(self):
        self.engine(self.alpha, "on")
        s = self.load()
        for key in THEME_KEYS:
            s.pop(key)
        s["enabledPlugins"]["tovar-themes-beta@local"] = True
        self.assertEqual(s, BASE)

    def test_on_without_enabled_plugins_list(self):
        self.save({"theme": "dark"})
        r = self.engine(self.alpha, "on")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("enabledPlugins", self.load())

    def test_switching_themes(self):
        self.engine(self.alpha, "on")
        self.engine(self.beta, "on")
        s = self.load()
        self.assertEqual(s["spinnerTipsOverride"]["label"], "Betadex")
        self.assertFalse(s["enabledPlugins"]["tovar-themes-alpha@local"])
        self.assertTrue(s["enabledPlugins"]["tovar-themes-beta@local"])

    # --- off ---

    def test_off_removes_own_values(self):
        self.engine(self.alpha, "on")
        r = self.engine(self.alpha, "off")
        self.assertEqual(r.returncode, 0, r.stderr)
        s = self.load()
        self.assertFalse(THEME_KEYS & s.keys())
        self.assertEqual(s["statusLine"], BASE["statusLine"])
        self.assertEqual(len(self.backups("alpha")), 2)

    def test_off_leaves_other_theme_alone(self):
        self.engine(self.beta, "on")
        before = self.settings.read_text(encoding="utf-8")
        r = self.engine(self.alpha, "off")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.settings.read_text(encoding="utf-8"), before)
        self.assertIn("tovar-themes-beta", r.stdout)
        self.assertEqual(self.backups("alpha"), [])

    def test_off_leaves_foreign_values_alone(self):
        data = dict(BASE, spinnerTipsOverride={"tipsFile": "/somewhere/tips.json",
                                               "label": "Pokédex"})
        self.save(data)
        r = self.engine(self.alpha, "off")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.load(), data)
        self.assertIn("Pokédex", r.stdout)

    # --- shared safety ---

    def test_invalid_settings_are_not_overwritten(self):
        self.settings.write_text("{ not json", encoding="utf-8")
        for cmd in ("on", "off"):
            r = self.engine(self.alpha, cmd)
            self.assertNotEqual(r.returncode, 0, cmd)
            self.assertIn("not valid JSON", r.stderr)
            self.assertEqual(self.settings.read_text(encoding="utf-8"), "{ not json")

    def test_missing_settings_file(self):
        self.settings.unlink()
        r = self.engine(self.alpha, "on")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("No settings file", r.stderr)
        self.assertFalse(self.settings.exists())

    def test_backups_in_same_second_do_not_overwrite(self):
        for _ in range(3):
            self.engine(self.alpha, "on")
        self.assertEqual(len(self.backups("alpha")), 3)

    def test_on_replaces_settings_file_atomically(self):
        before = self.settings.stat().st_ino
        self.engine(self.alpha, "on")
        self.assertNotEqual(self.settings.stat().st_ino, before)
        self.assertEqual(list(self.cfg.glob("*.tmp")), [])

    def test_symlinked_settings_stay_symlinked(self):
        real = self.cfg / "real-settings.json"
        self.settings.rename(real)
        self.settings.symlink_to(real)
        self.engine(self.alpha, "on")
        self.assertTrue(self.settings.is_symlink())
        self.assertIn("spinnerVerbs", json.loads(real.read_text(encoding="utf-8")))

    def test_non_ascii_text_survives(self):
        self.engine(self.beta, "on")
        self.assertIn("Béta verb 0", self.settings.read_text(encoding="utf-8"))

    # --- name hook ---

    def test_name_hook_renames_and_keeps_fields(self):
        event = {"tool_name": "Agent", "tool_input": {
            "description": "old", "prompt": "do it", "subagent_type": "Explore"}}
        seen = set()
        for _ in range(30):
            r = self.engine(self.alpha, "name", json.dumps(event))
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout)["hookSpecificOutput"]
            self.assertEqual(out["hookEventName"], "PreToolUse")
            tool_input = out["updatedInput"]
            self.assertEqual(tool_input, out["updatedToolInput"])
            self.assertEqual(tool_input["prompt"], "do it")
            self.assertEqual(tool_input["subagent_type"], "Explore")
            seen.add(tool_input["description"])
        self.assertEqual(seen, {"Neo", "Marty McFly"})

    def test_name_hook_is_silent_on_bad_input(self):
        for bad in ["", "not json", "[1, 2]"]:
            r = self.engine(self.alpha, "name", bad)
            self.assertEqual((r.returncode, r.stdout), (0, ""), bad)

    def test_name_hook_is_silent_without_names(self):
        path = self.alpha / "theme.json"
        c = json.loads(path.read_text(encoding="utf-8"))
        c["names"] = []
        path.write_text(json.dumps(c), encoding="utf-8")
        r = self.engine(self.alpha, "name", json.dumps({"tool_input": {}}))
        self.assertEqual((r.returncode, r.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
