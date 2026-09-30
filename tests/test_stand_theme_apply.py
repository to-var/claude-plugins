import json
import unittest

from stand_helpers import StandCase, ns, sample_theme
from engine import StandError, files, state, theme


class ApplyTest(StandCase):
    def setUp(self):
        super().setUp()
        theme.run(ns("create", "one", file=str(self.draft(sample_theme("One")))))
        theme.run(ns("create", "two", file=str(self.draft(sample_theme("Two"), name="two.json"))))

    def test_apply_writes_the_three_keys_the_tips_and_names(self):
        result = theme.run(ns("apply", "one"))
        settings = self.settings()
        self.assertEqual(settings["spinnerVerbs"], {"mode": "replace", "verbs": [f"Verb {i}" for i in range(40)]})
        self.assertEqual(len(settings["companyAnnouncements"]), 20)
        tips_file = self.data / "active" / "theme" / "tips.json"
        self.assertEqual(settings["spinnerTipsOverride"], {"tipsFile": str(tips_file), "label": "Holocron"})
        self.assertEqual(len(self.read_json(tips_file)), 20)
        self.assertEqual(self.read_json(self.data / "active" / "theme" / "names.json")[0], "Name 0")
        self.assertEqual(state.load()["theme"], "one")
        self.assertIn("Restart", result.message)

    def test_apply_keeps_other_settings_and_key_order(self):
        (self.config / "settings.json").write_text(
            '{\n  "zeta": 1,\n  "model": "opus",\n  "spinnerVerbs": {"mode": "append", "verbs": ["x"]},\n  "alpha": 2\n}\n',
            encoding="utf-8")
        theme.run(ns("apply", "one"))
        settings = self.settings()
        self.assertEqual(list(settings)[:4], ["zeta", "model", "spinnerVerbs", "alpha"])
        self.assertEqual((settings["zeta"], settings["model"], settings["alpha"]), (1, "opus", 2))

    def test_apply_backs_up_the_settings_file(self):
        (self.config / "settings.json").write_text('{"model": "opus"}\n', encoding="utf-8")
        result = theme.run(ns("apply", "one"))
        self.assertIn("Backup:", result.lines[-1])
        stamp = files.list_backups()[0]["name"]
        files.restore(stamp)
        self.assertEqual(self.settings(), {"model": "opus"})

    def test_apply_dry_run_changes_nothing(self):
        (self.config / "settings.json").write_text('{"model": "opus"}\n', encoding="utf-8")
        result = theme.run(ns("apply", "one", dry_run=True))
        self.assertIn("Dry run", result.message)
        self.assertEqual(self.settings(), {"model": "opus"})
        self.assertFalse((self.data / "active").exists())
        self.assertIsNone(state.load()["theme"])

    def test_apply_with_invalid_settings_stops_and_changes_nothing(self):
        (self.config / "settings.json").write_text("{oops", encoding="utf-8")
        with self.assertRaises(StandError):
            theme.run(ns("apply", "one"))
        self.assertEqual((self.config / "settings.json").read_text(encoding="utf-8"), "{oops")
        self.assertFalse((self.data / "active").exists())

    def test_apply_creates_the_settings_file_when_missing(self):
        theme.run(ns("apply", "one"))
        self.assertIn("spinnerVerbs", self.settings())

    def test_apply_twice_changes_nothing_the_second_time(self):
        theme.run(ns("apply", "one"))
        before = (self.config / "settings.json").read_bytes()
        result = theme.run(ns("apply", "one"))
        self.assertEqual((self.config / "settings.json").read_bytes(), before)
        self.assertEqual(result.lines, [])

    def test_switching_themes_replaces_the_values(self):
        theme.run(ns("apply", "one"))
        theme.run(ns("apply", "two"))
        self.assertEqual(state.load()["theme"], "two")
        self.assertEqual(theme.active_name(), "two")
        self.assertEqual(len(self.read_json(self.data / "active" / "theme" / "tips.json")), 20)
        self.assertIn("Subagents get Two names.", self.read_json(self.data / "active" / "theme" / "tips.json")[0])

    def test_off_removes_only_the_three_keys(self):
        (self.config / "settings.json").write_text('{"model": "opus"}\n', encoding="utf-8")
        theme.run(ns("apply", "one"))
        result = theme.run(ns("off"))
        self.assertEqual(self.settings(), {"model": "opus"})
        self.assertIsNone(state.load()["theme"])
        self.assertFalse((self.data / "active" / "theme" / "names.json").exists())
        self.assertIn("Off", result.message)

    def test_off_when_nothing_is_active_changes_nothing(self):
        (self.config / "settings.json").write_text('{"model": "opus"}\n', encoding="utf-8")
        result = theme.run(ns("off"))
        self.assertIn("Nothing changed", result.message)
        self.assertFalse((self.data / "backups").exists())

    def test_off_leaves_a_theme_that_stand_did_not_write(self):
        other = {"spinnerVerbs": {"mode": "replace", "verbs": ["x"]},
                 "spinnerTipsOverride": {"tipsFile": "/elsewhere/tips.json", "label": "Other"}}
        (self.config / "settings.json").write_text(json.dumps(other), encoding="utf-8")
        result = theme.run(ns("off"))
        self.assertIn("Nothing changed", result.message)
        self.assertEqual(self.settings(), other)

    def test_active_name_follows_the_real_settings_after_a_restore(self):
        (self.config / "settings.json").write_text('{"model": "opus"}\n', encoding="utf-8")
        theme.run(ns("apply", "one"))
        self.assertEqual(theme.active_name(), "one")
        files.restore(files.list_backups()[0]["name"])
        self.assertEqual(state.load()["theme"], "one")        # state is stale on purpose
        self.assertIsNone(theme.active_name())                # the real file says nothing is active
        self.assertFalse(any(r["active"] for r in theme.run(ns("list")).data))

    def test_apply_an_unknown_theme_is_a_clear_error(self):
        with self.assertRaises(StandError):
            theme.run(ns("apply", "nope"))


class HookTest(StandCase):
    def setUp(self):
        super().setUp()
        theme.run(ns("create", "one", file=str(self.draft(sample_theme("One")))))
        theme.run(ns("apply", "one"))
        self.event = json.dumps({"tool_name": "Agent", "tool_input": {"prompt": "hi", "description": "old"}})

    def test_hook_gives_the_subagent_a_theme_name(self):
        out = json.loads(theme.hook_name(self.event))
        update = out["hookSpecificOutput"]["updatedInput"]
        self.assertTrue(update["description"].startswith("Name "))
        self.assertEqual(update["prompt"], "hi")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "allow")
        self.assertEqual(out["hookSpecificOutput"]["updatedToolInput"], update)

    def test_hook_is_silent_without_an_active_theme(self):
        theme.run(ns("off"))
        self.assertIsNone(theme.hook_name(self.event))

    def test_hook_never_raises(self):
        for raw in ("", "not json", "[]", "null", json.dumps({"tool_input": 5})):
            theme.hook_name(raw)          # must not raise
        self.assertIsNone(theme.hook_name("not json"))

    def test_hook_keeps_accents(self):
        names = [f"Pokémon {i}" for i in range(100)]
        theme.run(ns("create", "poke", file=str(self.draft(sample_theme("Pokémon", names=names), name="p.json"))))
        theme.run(ns("apply", "poke"))
        self.assertIn("Pokémon", theme.hook_name(self.event))


if __name__ == "__main__":
    unittest.main()
