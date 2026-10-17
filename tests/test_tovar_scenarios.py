"""User scenarios the area tests leave open: odd settings files, CRLF, names, errors and undo."""
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

from tovar_helpers import SCRIPTS, TovarCase, ns, sample_theme
from engine import TovarError, files, memory, state, style, theme

STYLE = "---\nname: Plain\ndescription: short and plain\n---\n\nWrite in plain words.\n"


class ThemeSettingsFileTest(TovarCase):
    def setUp(self):
        super().setUp()
        theme.run(ns("create", "one", file=str(self.draft(sample_theme("One")))))
        self.path = self.config / "settings.json"

    def test_apply_on_an_empty_settings_file_writes_the_theme(self):
        for empty in ("", "  \n"):
            self.path.write_text(empty, encoding="utf-8")
            theme.run(ns("apply", "one"))
            self.assertEqual(theme.active_name(), "one")
            self.assertEqual(set(self.settings()), {"spinnerVerbs", "companyAnnouncements", "spinnerTipsOverride"})
            theme.run(ns("off"))

    def test_apply_backs_up_an_empty_settings_file_so_undo_brings_it_back(self):
        for empty in ("", "  \n"):
            self.path.write_text(empty, encoding="utf-8")
            theme.run(ns("apply", "one"))
            files.restore(files.list_backups()[0]["name"])
            self.assertEqual(self.path.read_text(encoding="utf-8"), empty)
            self.assertIsNone(theme.active_name())

    def test_off_and_status_on_an_empty_settings_file_change_nothing(self):
        for empty in ("", "  \n"):
            self.path.write_text(empty, encoding="utf-8")
            self.assertIn("Nothing changed", theme.run(ns("off")).message)
            self.assertIn("Nothing changed", style.run(ns("off")).message)
            r = self.run_cli("status")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("theme: none", r.stdout)
            self.assertIn("style: none", r.stdout)
            self.assertEqual(self.path.read_text(encoding="utf-8"), empty)
        self.assertFalse((self.data / "backups").exists())

    def test_apply_and_off_keep_unrelated_keys_exactly(self):
        mine = {"model": "opus", "permissions": {"allow": ["Bash(ls)"]}, "env": {"A": "é"}}
        self.path.write_text(json.dumps(mine), encoding="utf-8")
        theme.run(ns("apply", "one"))
        self.assertEqual({k: self.settings()[k] for k in mine}, mine)
        theme.run(ns("off"))
        self.assertEqual(self.settings(), mine)

    def test_off_and_status_leave_a_broken_settings_file_untouched(self):
        theme.run(ns("apply", "one"))
        self.path.write_text("{oops", encoding="utf-8")
        with self.assertRaises(TovarError):
            theme.run(ns("off"))
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{oops")
        r = self.run_cli("status")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not valid JSON", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{oops")

    def test_a_settings_file_that_is_not_an_object_is_refused_untouched(self):
        self.path.write_text("[1, 2]\n", encoding="utf-8")
        with self.assertRaises(TovarError) as caught:
            theme.run(ns("apply", "one"))
        self.assertIn("not a JSON object", str(caught.exception))
        self.assertEqual(self.path.read_text(encoding="utf-8"), "[1, 2]\n")
        self.assertFalse((self.data / "active").exists())


class ThemeLifecycleTest(TovarCase):
    def setUp(self):
        super().setUp()
        theme.run(ns("create", "one", file=str(self.draft(sample_theme("One")))))

    def test_update_with_a_new_display_regenerates_the_plugin_tips(self):
        theme.run(ns("update", "one", file=str(self.draft(sample_theme("Renamed"), name="r.json"))))
        tips = theme.read_theme(self.data / "themes" / "one")["tips"]
        self.assertEqual(tips[:5], theme.plugin_tips("Renamed"))
        self.assertEqual(len(tips), 20)
        self.assertFalse(any("One names" in t for t in tips))

    def test_an_updated_active_theme_reaches_settings_only_after_apply(self):
        theme.run(ns("apply", "one"))
        newer = sample_theme("One", verbs=[f"New verb {i}" for i in range(40)])
        theme.run(ns("update", "one", file=str(self.draft(newer, name="n.json"))))
        self.assertEqual(self.settings()["spinnerVerbs"]["verbs"][0], "Verb 0")
        theme.run(ns("apply", "one"))
        self.assertEqual(self.settings()["spinnerVerbs"]["verbs"][0], "New verb 0")

    def test_apply_writes_every_name_and_tip_to_the_active_folder(self):
        theme.run(ns("apply", "one"))
        folder = self.data / "active" / "theme" / "one"
        self.assertEqual(self.read_json(folder / "names.json"), [f"Name {i}" for i in range(100)])
        self.assertEqual(self.read_json(folder / "tips.json")[:5], theme.plugin_tips("One"))
        self.assertEqual(theme.run(ns("active")).data["names"], [f"Name {i}" for i in range(100)])

    def test_apply_dry_run_shows_the_settings_diff(self):
        result = theme.run(ns("apply", "one", dry_run=True))
        self.assertTrue(any("spinnerVerbs" in line for line in result.lines))
        self.assertFalse((self.config / "settings.json").exists())

    def test_export_dry_run_writes_nothing(self):
        result = theme.run(ns("export", "one", to=str(self.tmp / "out"), dry_run=True))
        self.assertIn("Dry run", result.message)
        self.assertFalse((self.tmp / "out").exists())

    def test_check_with_no_names_checks_yours_and_examples(self):
        folder = self.examples / "themes" / "shipped"
        for name, text in theme.item_files(theme.normalize(sample_theme("Shipped"))).items():
            (folder / name).parent.mkdir(parents=True, exist_ok=True)
            (folder / name).write_text(text, encoding="utf-8")
        result = theme.run(ns("check"))
        self.assertEqual(result.lines, ["one: OK", "shipped: OK"])

    def test_shipped_example_themes_pass_check_and_apply(self):
        with mock.patch.dict(os.environ, {"TOVAR_EXAMPLES": str(SCRIPTS.parent / "examples")}):
            result = theme.run(ns("check"))
            self.assertTrue(result.ok, result.lines)
            theme.run(ns("apply", "pokemon"))
            self.assertEqual(theme.active_name(), "pokemon")


class NameRulesTest(TovarCase):
    def test_every_area_refuses_bad_names(self):
        draft_md = self.tmp / "d.md"
        draft_md.write_text(STYLE, encoding="utf-8")
        for bad in ("Bad Name", "../x", "a_b", "-a", "a-", "UPPER", ""):
            with self.assertRaises(TovarError, msg=bad):
                theme.run(ns("create", bad, file=str(self.draft())))
            with self.assertRaises(TovarError, msg=bad):
                style.run(ns("create", bad, file=str(draft_md)))
            with self.assertRaises(TovarError, msg=bad):
                memory.run(ns("create", bad, file=str(draft_md)))
        self.assertFalse((self.data / "themes").exists())
        self.assertFalse((self.data / "styles").exists())
        self.assertFalse((self.data / "memory").exists())

    def test_a_missing_draft_file_is_a_clear_error(self):
        for area in (style, memory):
            with self.assertRaises(TovarError) as caught:
                area.run(ns("create", "x", file=str(self.tmp / "missing.md")))
            self.assertIn("not found", str(caught.exception))


class StyleScenarioTest(TovarCase):
    def setUp(self):
        super().setUp()
        path = self.tmp / "plain.md"
        path.write_text(STYLE, encoding="utf-8")
        style.run(ns("create", "plain", file=str(path)))
        self.out = self.config / "output-styles"

    def test_apply_on_an_empty_settings_file(self):
        (self.config / "settings.json").write_text("", encoding="utf-8")
        style.run(ns("apply", "plain"))
        self.assertEqual(self.settings(), {"outputStyle": "Plain"})
        self.assertTrue((self.out / "tovar-plain.md").is_file())

    def test_active_needs_the_tovar_prefix_and_a_matching_frontmatter_name(self):
        (self.config / "settings.json").write_text('{"outputStyle": "Plain"}', encoding="utf-8")
        self.out.mkdir()
        (self.out / "plain.md").write_text(STYLE, encoding="utf-8")         # the user's own file
        self.assertIsNone(style.active_name())
        (self.out / "tovar-plain.md").write_text(STYLE.replace("name: Plain", "name: Other"), encoding="utf-8")
        self.assertIsNone(style.active_name())
        (self.out / "tovar-plain.md").write_text(STYLE, encoding="utf-8")
        self.assertEqual(style.active_name(), "plain")

    def test_off_never_touches_the_users_own_style_files(self):
        self.out.mkdir()
        (self.out / "mine.md").write_text("my own", encoding="utf-8")
        style.run(ns("apply", "plain"))
        style.run(ns("off"))
        self.assertEqual((self.out / "mine.md").read_text(encoding="utf-8"), "my own")
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ["mine.md"])

    def test_off_leaves_a_broken_settings_file_untouched(self):
        style.run(ns("apply", "plain"))
        (self.config / "settings.json").write_text("{oops", encoding="utf-8")
        with self.assertRaises(TovarError):
            style.run(ns("off"))
        self.assertEqual((self.config / "settings.json").read_text(encoding="utf-8"), "{oops")
        self.assertTrue((self.out / "tovar-plain.md").exists())

    def test_off_dry_run_changes_nothing(self):
        style.run(ns("apply", "plain"))
        result = style.run(ns("off", dry_run=True))
        self.assertIn("Dry run", result.message)
        self.assertEqual(style.active_name(), "plain")


class MemoryScenarioTest(TovarCase):
    def setUp(self):
        super().setUp()
        for name, text in (("a", "Rule A\n"), ("b", "Rule B\r\nline two\r\n")):
            path = self.tmp / f"{name}.md"
            path.write_bytes(text.encode("utf-8"))
            memory.run(ns("create", name, file=str(path)))
        self.md = self.config / "CLAUDE.md"

    def test_text_outside_the_block_is_kept_byte_for_byte(self):
        top = "# Mine  \n\tTabbed line\n\nPokémon é <!-- a comment -->\n"
        self.md.write_bytes(top.encode("utf-8"))
        memory.run(ns("enable", "a"))
        text = self.md.read_bytes().decode("utf-8")
        self.assertTrue(text.startswith(top))
        bottom = "\n\nBelow the block  \n\twith a tab\n"
        self.md.write_bytes((text.rstrip("\n") + bottom).encode("utf-8"))
        memory.run(ns("enable", "b"))
        memory.run(ns("order", "b", "a"))
        memory.run(ns("apply"))
        after = self.md.read_bytes().decode("utf-8")
        self.assertTrue(after.startswith(top))
        self.assertTrue(after.endswith(bottom))
        self.assertLess(after.index("Rule B"), after.index("Rule A"))

    def test_a_crlf_claude_md_stays_crlf_through_enable_and_disable(self):
        self.md.write_bytes(b"# Mine\r\nKeep me.\r\n")
        memory.run(ns("enable", "a"))
        memory.run(ns("enable", "b"))
        raw = self.md.read_bytes()
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))
        self.assertIn(b"Rule B\r\nline two\r\n", raw)
        self.assertEqual(memory.enabled(), ["a", "b"])
        memory.run(ns("disable", "a"))
        memory.run(ns("disable", "b"))
        self.assertEqual(self.md.read_bytes(), b"# Mine\r\nKeep me.\r\n")

    def test_a_broken_block_stops_disable_order_and_apply_too(self):
        memory.run(ns("enable", "a"))
        broken = self.md.read_text(encoding="utf-8") + f"\n{memory.START}\n"
        self.md.write_text(broken, encoding="utf-8")
        for args in (ns("disable", "a"), ns("order", "a"), ns("apply"), ns("enable", "b")):
            with self.assertRaises(TovarError):
                memory.run(args)
        self.assertEqual(self.md.read_text(encoding="utf-8"), broken)

    def test_apply_with_nothing_enabled_leaves_claude_md_alone(self):
        self.md.write_text("mine\n", encoding="utf-8")
        result = memory.run(ns("apply"))
        self.assertEqual(result.lines, [])
        self.assertEqual(self.md.read_text(encoding="utf-8"), "mine\n")

    def test_enable_of_an_unknown_snippet_is_a_clear_error(self):
        with self.assertRaises(TovarError) as caught:
            memory.run(ns("enable", "nope"))
        self.assertIn("No memory item named 'nope'", str(caught.exception))
        self.assertFalse(self.md.exists())


class UndoTest(TovarCase):
    def setUp(self):
        super().setUp()
        theme.run(ns("create", "one", file=str(self.draft(sample_theme("One")))))

    def test_status_shows_theme_style_and_memory(self):
        style_path = self.tmp / "plain.md"
        style_path.write_text(STYLE, encoding="utf-8")
        style.run(ns("create", "plain", file=str(style_path)))
        snippet = self.tmp / "a.md"
        snippet.write_text("Rule A\n", encoding="utf-8")
        memory.run(ns("create", "a", file=str(snippet)))
        theme.run(ns("apply", "one"))
        style.run(ns("apply", "plain"))
        memory.run(ns("enable", "a"))
        r = self.run_cli("status")
        self.assertEqual(r.returncode, 0, r.stderr)
        for line in ("theme: one", "style: plain", "memory: a", f"data folder: {self.data}",
                     f"config folder: {self.config}"):
            self.assertIn(line, r.stdout)

    def test_status_with_nothing_applied(self):
        r = self.run_cli("status")
        self.assertEqual(r.returncode, 0, r.stderr)
        for line in ("theme: none", "style: none", "memory: none"):
            self.assertIn(line, r.stdout)

    def test_restore_with_no_backups_says_so(self):
        r = self.run_cli("restore")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("(no backups yet)", r.stdout)

    def test_backups_are_listed_newest_first(self):
        (self.config / "settings.json").write_text('{"model": "opus"}\n', encoding="utf-8")
        stamp = lambda result: result.lines[-1].split("Backup: ")[1].split(" ")[0]
        applied = stamp(theme.run(ns("apply", "one")))
        turned_off = stamp(theme.run(ns("off")))
        self.assertNotEqual(applied, turned_off)
        listed = json.loads(self.run_cli("restore", "--json").stdout)["data"]
        self.assertEqual([b["name"] for b in listed], [turned_off, applied])

    def test_restore_dry_run_writes_nothing(self):
        (self.config / "settings.json").write_text('{"model": "opus"}\n', encoding="utf-8")
        theme.run(ns("apply", "one"))
        before = (self.config / "settings.json").read_bytes()
        name = files.list_backups()[0]["name"]
        r = self.run_cli("restore", name, "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Dry run", r.stdout)
        self.assertEqual((self.config / "settings.json").read_bytes(), before)
        self.assertEqual(len(files.list_backups()), 1)

    def test_restore_after_apply_on_no_settings_deletes_the_created_file(self):
        theme.run(ns("apply", "one"))
        self.assertTrue((self.config / "settings.json").exists())
        files.restore(files.list_backups()[0]["name"])
        self.assertFalse((self.config / "settings.json").exists())
        self.assertIsNone(theme.active_name())

    def test_restore_of_an_unknown_backup_fails_cleanly(self):
        r = self.run_cli("restore", "20200101-000000")
        self.assertEqual(r.returncode, 1)
        self.assertIn("No backup named", r.stderr)
        self.assertNotIn("Traceback", r.stderr)


class CommandLineErrorTest(TovarCase):
    def run_without_data(self, *args):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_DATA"}
        return subprocess.run([sys.executable, str(SCRIPTS / "tovar.py"), *args],
                              capture_output=True, text=True, encoding="utf-8", env=env)

    def test_a_missing_data_folder_is_a_clear_error(self):
        for args in (("theme", "list"), ("status",), ("restore",), ("memory", "enable", "a")):
            r = self.run_without_data(*args)
            self.assertEqual(r.returncode, 1, args)
            self.assertIn("--data", r.stderr)
            self.assertNotIn("Traceback", r.stderr)

    def test_an_area_with_no_action_names_the_actions(self):
        for area in ("theme", "style", "memory"):
            r = self.run_cli(area)
            self.assertEqual(r.returncode, 1)
            self.assertIn("Say what to do with", r.stderr)

    def test_an_unknown_area_is_refused_by_the_parser(self):
        r = self.run_cli("bogus")
        self.assertEqual(r.returncode, 2)
        self.assertIn("invalid choice", r.stderr)


if __name__ == "__main__":
    unittest.main()
