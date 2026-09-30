import unittest

from stand_helpers import StandCase
from engine import StandError, files, items


class AreaTest(StandCase):
    def setUp(self):
        super().setUp()
        self.notes = items.Area("notes", folder=False)
        self.boxes = items.Area("boxes", folder=True)
        (self.examples / "notes").mkdir()
        (self.data / "notes").mkdir()
        (self.examples / "notes" / "sample.md").write_text("example", encoding="utf-8")
        (self.examples / "notes" / "readonly.md").write_text("example", encoding="utf-8")
        (self.data / "notes" / "sample.md").write_text("mine", encoding="utf-8")
        (self.data / "notes" / "mine.md").write_text("mine", encoding="utf-8")

    def test_yours_hides_the_example_with_the_same_name(self):
        rows = {e.name: e.source for e in self.notes.entries()}
        self.assertEqual(rows, {"mine": "yours", "readonly": "example", "sample": "yours"})

    def test_entries_are_sorted_by_name(self):
        self.assertEqual([e.name for e in self.notes.entries()], ["mine", "readonly", "sample"])

    def test_resolve_finds_or_explains(self):
        self.assertEqual(self.notes.resolve("readonly").source, "example")
        with self.assertRaises(StandError) as caught:
            self.notes.resolve("nope")
        self.assertIn("nope", str(caught.exception))

    def test_new_names_are_checked(self):
        for bad in ["Bad Name", "../x", "-a", ""]:
            with self.assertRaises(StandError):
                self.notes.check_new_name(bad)
        with self.assertRaises(StandError):
            self.notes.check_new_name("mine")
        self.notes.check_new_name("readonly")     # only an example: allowed, it will hide it

    def test_examples_cannot_be_changed(self):
        with self.assertRaises(StandError) as caught:
            self.notes.require_yours("readonly")
        self.assertIn("--from readonly", str(caught.exception))
        self.assertEqual(self.notes.require_yours("mine").source, "yours")

    def test_copy_makes_your_own_file(self):
        self.notes.copy(self.notes.resolve("readonly"), "copy")
        self.assertEqual((self.data / "notes" / "copy.md").read_text(encoding="utf-8"), "example")

    def test_delete_backs_up_so_restore_brings_it_back(self):
        stamp, _ = self.notes.delete("mine", dry_run=False)
        self.assertFalse((self.data / "notes" / "mine.md").exists())
        files.restore(stamp)
        self.assertEqual((self.data / "notes" / "mine.md").read_text(encoding="utf-8"), "mine")

    def test_delete_dry_run_changes_nothing_and_examples_are_refused(self):
        self.notes.delete("mine", dry_run=True)
        self.assertTrue((self.data / "notes" / "mine.md").exists())
        with self.assertRaises(StandError):
            self.notes.delete("readonly", dry_run=False)

    def test_folder_items_need_their_marker_file(self):
        (self.data / "boxes" / "good").mkdir(parents=True)
        (self.data / "boxes" / "good" / "settings.json").write_text("{}", encoding="utf-8")
        (self.data / "boxes" / "empty").mkdir()
        self.assertEqual([e.name for e in self.boxes.entries()], ["good"])

    def test_deleting_a_folder_item_removes_the_folder(self):
        folder = self.data / "boxes" / "good"
        folder.mkdir(parents=True)
        (folder / "settings.json").write_text("{}", encoding="utf-8")
        (folder / "tips.json").write_text("[]", encoding="utf-8")
        stamp, _ = self.boxes.delete("good", dry_run=False)
        self.assertFalse(folder.exists())
        files.restore(stamp)
        self.assertTrue((folder / "tips.json").is_file())


class HelpersTest(StandCase):
    def test_list_result_marks_active_items(self):
        area = items.Area("notes", folder=False)
        (self.data / "notes").mkdir()
        (self.data / "notes" / "a.md").write_text("x", encoding="utf-8")
        (self.data / "notes" / "b.md").write_text("x", encoding="utf-8")
        result = items.list_result(area, lambda name: name == "b")
        self.assertEqual([r["active"] for r in result.data], [False, True])
        self.assertTrue(result.lines[1].startswith("*"))
        self.assertEqual(items.list_result(items.Area("empty", folder=False), lambda n: False).lines, ["(none)"])

    def test_one_name_needs_exactly_one(self):
        self.assertEqual(items.one_name("show", ["a"]), "a")
        for names in ([], ["a", "b"]):
            with self.assertRaises(StandError):
                items.one_name("show", names)

    def test_write_result_dry_run_and_real(self):
        dry = items.write_result("Saved.", None, ["+x"], dry_run=True)
        self.assertIn("Dry run", dry.message)
        self.assertEqual(dry.lines, ["+x"])
        real = items.write_result("Saved.", "20260101-000000", ["Wrote a"], dry_run=False)
        self.assertEqual(real.message, "Saved.")
        self.assertIn("restore 20260101-000000", real.lines[-1])

    def test_unknown_action_names_the_valid_ones(self):
        text = items.unknown_action("theme", "explode")
        self.assertIn("explode", text)
        self.assertIn("apply", text)


if __name__ == "__main__":
    unittest.main()
