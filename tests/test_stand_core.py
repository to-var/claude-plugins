import os
import unittest
from unittest import mock

from stand_helpers import StandCase
from engine import StandError, files, paths, state
from engine.files import Change


class PathsTest(StandCase):
    def test_data_dir_needs_the_variable(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("CLAUDE_PLUGIN_DATA")
            with self.assertRaises(StandError):
                paths.data_dir()

    def test_folders_follow_the_environment(self):
        self.assertEqual(paths.data_dir(), self.data)
        self.assertEqual(paths.config_dir(), self.config)
        self.assertEqual(paths.examples_dir(), self.examples)
        self.assertEqual(paths.settings_path(), self.config / "settings.json")
        self.assertEqual(paths.claude_md_path(), self.config / "CLAUDE.md")
        self.assertEqual(paths.styles_dir(), self.config / "output-styles")


class ApplyChangesTest(StandCase):
    def test_writes_and_backs_up_a_changed_file(self):
        target = self.config / "settings.json"
        target.write_text('{"a": 1}\n', encoding="utf-8")
        stamp, lines = files.apply_changes([Change(target, '{"a": 2}\n')])
        self.assertEqual(target.read_text(encoding="utf-8"), '{"a": 2}\n')
        saved = self.data / "backups" / stamp / "1-settings.json"
        self.assertEqual(saved.read_text(encoding="utf-8"), '{"a": 1}\n')
        self.assertIn(f"Wrote {target}", lines)

    def test_dry_run_writes_nothing_and_shows_a_diff(self):
        target = self.config / "CLAUDE.md"
        target.write_text("old\n", encoding="utf-8")
        stamp, lines = files.apply_changes([Change(target, "new\n")], dry_run=True)
        self.assertIsNone(stamp)
        self.assertEqual(target.read_text(encoding="utf-8"), "old\n")
        self.assertTrue(any(l.startswith("-old") for l in lines))
        self.assertTrue(any(l.startswith("+new") for l in lines))
        self.assertFalse((self.data / "backups").exists())

    def test_unchanged_file_is_skipped_without_a_backup(self):
        target = self.config / "a.txt"
        target.write_text("same", encoding="utf-8")
        stamp, lines = files.apply_changes([Change(target, "same")])
        self.assertIsNone(stamp)
        self.assertEqual(lines, [])
        self.assertFalse((self.data / "backups").exists())

    def test_delete_change_removes_the_file_and_backs_it_up(self):
        target = self.config / "a.txt"
        target.write_text("keep me", encoding="utf-8")
        stamp, _ = files.apply_changes([Change(target, None)])
        self.assertFalse(target.exists())
        files.restore(stamp)
        self.assertEqual(target.read_text(encoding="utf-8"), "keep me")

    def test_restore_deletes_files_the_change_created(self):
        target = self.config / "new.txt"
        stamp, _ = files.apply_changes([Change(target, "hi")])
        self.assertTrue(target.exists())
        files.restore(stamp)
        self.assertFalse(target.exists())

    def test_restore_puts_the_old_text_back_and_backs_up_the_current_one(self):
        target = self.config / "a.txt"
        target.write_text("v1", encoding="utf-8")
        stamp, _ = files.apply_changes([Change(target, "v2")])
        newer, _ = files.restore(stamp)
        self.assertEqual(target.read_text(encoding="utf-8"), "v1")
        self.assertTrue(newer)
        self.assertEqual(len(files.list_backups()), 2)

    def test_restore_dry_run_shows_the_whole_diff(self):
        target = self.config / "big.txt"
        target.write_text("".join(f"old {i}\n" for i in range(200)), encoding="utf-8")
        stamp, _ = files.apply_changes([Change(target, "".join(f"new {i}\n" for i in range(200)))])
        _, lines = files.restore(stamp, dry_run=True)
        self.assertGreater(len(lines), 400)
        self.assertFalse(any("more lines" in line for line in lines))

    def test_files_marked_no_backup_are_not_recorded(self):
        target = self.config / "tips.json"
        stamp, _ = files.apply_changes([Change(target, "[]", backup=False)])
        self.assertIsNone(stamp)
        self.assertTrue(target.exists())
        self.assertFalse((self.data / "backups").exists())

    def test_restore_rejects_path_tricks_and_unknown_names(self):
        with self.assertRaises(StandError):
            files.restore("../x")
        with self.assertRaises(StandError):
            files.restore("20200101-000000")

    def test_line_endings_survive_a_round_trip(self):
        target = self.config / "CLAUDE.md"
        target.write_bytes(b"a\r\nb\r\n")
        text = files.read_text(target)
        self.assertEqual(text, "a\r\nb\r\n")
        files.apply_changes([Change(target, text + "c\r\n")])
        self.assertEqual(target.read_bytes(), b"a\r\nb\r\nc\r\n")

    def test_invalid_json_names_the_file(self):
        target = self.config / "settings.json"
        target.write_text("{oops", encoding="utf-8")
        with self.assertRaises(StandError) as caught:
            files.read_json_file(target)
        self.assertIn(str(target), str(caught.exception))
        self.assertIsNone(files.read_json_file(self.config / "missing.json"))

    def test_accents_survive_a_round_trip(self):
        target = self.config / "a.json"
        files.apply_changes([Change(target, files.dump_json({"n": "Pokémon"}))])
        self.assertEqual(files.read_json_file(target), {"n": "Pokémon"})
        self.assertIn("Pokémon", target.read_text(encoding="utf-8"))


class StateTest(StandCase):
    def test_default_state(self):
        self.assertEqual(state.load(), {"theme": None, "style": None, "style_setting": None, "memory": []})

    def test_round_trip(self):
        st = state.load()
        st["theme"] = "star-wars"
        st["memory"].append("a")
        state.save(st)
        self.assertEqual(state.load()["theme"], "star-wars")
        self.assertEqual(state.load()["memory"], ["a"])
        self.assertEqual(state.load()["style"], None)


if __name__ == "__main__":
    unittest.main()
