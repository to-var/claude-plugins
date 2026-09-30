import json
import unittest

from stand_helpers import StandCase, ns
from engine import StandError, files, state, style

GOOD = "---\nname: Plain\ndescription: short and plain\nkeep-coding-instructions: true\n---\n\nWrite in plain words.\n"


class RulesTest(StandCase):
    def test_frontmatter_parses(self):
        fm, body = style.parse_frontmatter(GOOD)
        self.assertEqual(fm["name"], "Plain")
        self.assertEqual(fm["keep-coding-instructions"], "true")
        self.assertIn("plain words", body)
        self.assertEqual(style.parse_frontmatter("no frontmatter"), ({}, "no frontmatter"))

    def test_problems(self):
        self.assertEqual(style.problems(GOOD), [])
        text = "\n".join(style.problems("---\nname: X\n---\n"))
        self.assertIn("description is missing", text)
        self.assertIn("no instructions", text)
        self.assertIn("name is missing", "\n".join(style.problems("just text")))


class StyleTest(StandCase):
    def draft_md(self, text=GOOD, name="draft.md"):
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def setUp(self):
        super().setUp()
        style.run(ns("create", "plain", file=self.draft_md()))

    def test_create_saves_the_file_and_refuses_bad_ones(self):
        self.assertEqual((self.data / "styles" / "plain.md").read_text(encoding="utf-8"), GOOD)
        with self.assertRaises(StandError):
            style.run(ns("create", "plain", file=self.draft_md()))
        with self.assertRaises(StandError):
            style.run(ns("create", "bad", file=self.draft_md("nothing here", "bad.md")))
        self.assertFalse((self.data / "styles" / "bad.md").exists())

    def test_create_from_an_example(self):
        (self.examples / "styles").mkdir()
        (self.examples / "styles" / "eli5.md").write_text(GOOD, encoding="utf-8")
        style.run(ns("create", "mine", from_="eli5"))
        self.assertEqual((self.data / "styles" / "mine.md").read_text(encoding="utf-8"), GOOD)

    def test_apply_writes_the_style_file_and_the_setting(self):
        (self.config / "settings.json").write_text('{"model": "opus"}\n', encoding="utf-8")
        result = style.run(ns("apply", "plain"))
        self.assertEqual((self.config / "output-styles" / "stand-plain.md").read_text(encoding="utf-8"), GOOD)
        self.assertEqual(self.settings(), {"model": "opus", "outputStyle": "Plain"})
        st = state.load()
        self.assertEqual((st["style"], st["style_setting"]), ("plain", "Plain"))
        self.assertIn("Restart", result.message)

    def test_apply_dry_run_and_invalid_settings_change_nothing(self):
        style.run(ns("apply", "plain", dry_run=True))
        self.assertFalse((self.config / "output-styles").exists())
        (self.config / "settings.json").write_text("{oops", encoding="utf-8")
        with self.assertRaises(StandError):
            style.run(ns("apply", "plain"))
        self.assertFalse((self.config / "output-styles").exists())

    def test_apply_twice_changes_nothing_and_switching_removes_the_old_file(self):
        style.run(ns("apply", "plain"))
        self.assertEqual(style.run(ns("apply", "plain")).lines, [])
        style.run(ns("create", "other", file=self.draft_md(GOOD.replace("Plain", "Other"), "o.md")))
        style.run(ns("apply", "other"))
        self.assertFalse((self.config / "output-styles" / "stand-plain.md").exists())
        self.assertEqual(self.settings()["outputStyle"], "Other")

    def test_off_removes_the_file_and_the_setting_only_if_stand_owns_it(self):
        style.run(ns("apply", "plain"))
        style.run(ns("off"))
        self.assertFalse((self.config / "output-styles" / "stand-plain.md").exists())
        self.assertNotIn("outputStyle", self.settings())
        self.assertIsNone(style.active_name())

    def test_off_leaves_a_style_the_user_picked_later(self):
        style.run(ns("apply", "plain"))
        settings = self.settings()
        settings["outputStyle"] = "Something else"
        (self.config / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
        result = style.run(ns("off"))
        self.assertIn("Nothing changed", result.message)
        self.assertEqual(self.settings()["outputStyle"], "Something else")

    def test_active_name_follows_a_restore(self):
        (self.config / "settings.json").write_text('{"model": "opus"}\n', encoding="utf-8")
        style.run(ns("apply", "plain"))
        self.assertEqual(style.active_name(), "plain")
        files.restore(files.list_backups()[0]["name"])
        self.assertIsNone(style.active_name())

    def test_update_and_delete_rules(self):
        style.run(ns("update", "plain", file=self.draft_md(GOOD.replace("plain words", "small words"), "n.md")))
        self.assertIn("small words", (self.data / "styles" / "plain.md").read_text(encoding="utf-8"))
        style.run(ns("apply", "plain"))
        self.assertIn("apply", style.run(ns("update", "plain", file=self.draft_md(GOOD, "n2.md"))).message)
        with self.assertRaises(StandError) as caught:
            style.run(ns("delete", "plain"))
        self.assertIn("turn it off", str(caught.exception))
        style.run(ns("off"))
        style.run(ns("delete", "plain"))
        self.assertFalse((self.data / "styles" / "plain.md").exists())

    def test_examples_cannot_be_updated_or_deleted(self):
        (self.examples / "styles").mkdir()
        (self.examples / "styles" / "eli5.md").write_text(GOOD, encoding="utf-8")
        for action in ("update", "delete"):
            with self.assertRaises(StandError):
                style.run(ns(action, "eli5", file=self.draft_md()))

    def test_show_check_list(self):
        self.assertIn("Write in plain words", "\n".join(style.run(ns("show", "plain")).lines))
        self.assertTrue(style.run(ns("check")).ok)
        (self.data / "styles" / "plain.md").write_text("broken", encoding="utf-8")
        self.assertFalse(style.run(ns("check", "plain")).ok)
        self.assertEqual(style.run(ns("list")).data[0]["name"], "plain")

    def test_unknown_action(self):
        with self.assertRaises(StandError):
            style.run(ns("explode", "x"))


if __name__ == "__main__":
    unittest.main()
