import unittest

from stand_helpers import StandCase, ns
from engine import StandError, files, memory, state

START, END = memory.START, memory.END


class MergeTest(unittest.TestCase):
    BLOCK = f"{START}\n<!-- stand:a -->\nRule A\n{END}"

    def test_missing_file_and_empty_file_get_just_the_block(self):
        self.assertEqual(memory.merge(None, self.BLOCK), self.BLOCK + "\n")
        self.assertEqual(memory.merge("", self.BLOCK), self.BLOCK + "\n")

    def test_no_block_and_no_file_stays_missing(self):
        self.assertIsNone(memory.merge(None, None))
        self.assertEqual(memory.merge("mine\n", None), "mine\n")

    def test_block_is_appended_after_existing_text_that_is_kept(self):
        for text in ("mine\n", "mine", "mine\n\n\n"):
            out = memory.merge(text, self.BLOCK)
            self.assertTrue(out.startswith("mine"))
            self.assertEqual(out, "mine\n\n" + self.BLOCK + "\n")

    def test_block_in_the_middle_is_replaced_and_outside_text_is_untouched(self):
        old = f"top\n\n{START}\nold\n{END}\n\nbottom\n"
        out = memory.merge(old, self.BLOCK)
        self.assertEqual(out, f"top\n\n{self.BLOCK}\n\nbottom\n")

    def test_applying_twice_is_the_same(self):
        once = memory.merge("mine\n", self.BLOCK)
        self.assertEqual(memory.merge(once, self.BLOCK), once)

    def test_removing_keeps_the_text_around_it(self):
        text = f"top\n\n{START}\nold\n{END}\n\nbottom\n"
        self.assertEqual(memory.merge(text, None), "top\n\nbottom\n")
        self.assertEqual(memory.merge(f"{START}\nold\n{END}\n", None), "")
        self.assertEqual(memory.merge(f"top\n\n{START}\nold\n{END}\n", None), "top\n")

    def test_windows_line_endings_are_kept(self):
        text = "top\r\nmore\r\n"
        out = memory.merge(text, self.BLOCK)
        self.assertEqual(out, "top\r\nmore\r\n\r\n" + self.BLOCK.replace("\n", "\r\n") + "\r\n")
        self.assertNotIn("\n", out.replace("\r\n", ""))
        back = memory.merge(out, None)
        self.assertEqual(back, "top\r\nmore\r\n")

    def test_half_or_repeated_or_reversed_markers_stop_the_write(self):
        for text in (f"a\n{START}\nb\n", f"a\n{END}\n", f"{END}\n{START}\n",
                     f"{START}\n{END}\n{START}\n{END}\n"):
            with self.assertRaises(StandError):
                memory.merge(text, self.BLOCK)
            with self.assertRaises(StandError):
                memory.merge(text, None)

    def test_render_orders_snippets_and_cleans_line_endings(self):
        block = memory.render([("a", "Rule A\r\n"), ("b", "Rule B\n")])
        self.assertEqual(block, f"{START}\n<!-- stand:a -->\nRule A\n\n<!-- stand:b -->\nRule B\n{END}")
        self.assertIsNone(memory.render([]))


class MemoryTest(StandCase):
    def setUp(self):
        super().setUp()
        for name, text in (("a", "Rule A\n"), ("b", "Rule B\n"), ("c", "Rule C\n")):
            path = self.tmp / f"{name}.md"
            path.write_text(text, encoding="utf-8")
            memory.run(ns("create", name, file=str(path)))
        self.md = self.config / "CLAUDE.md"

    def test_enable_writes_the_block_and_keeps_your_text(self):
        self.md.write_text("# Mine\n\nKeep me.\n", encoding="utf-8")
        memory.run(ns("enable", "a"))
        text = self.md.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Mine\n\nKeep me.\n"))
        self.assertIn("Rule A", text)
        self.assertEqual(state.load()["memory"], ["a"])

    def test_enable_creates_a_missing_claude_md(self):
        memory.run(ns("enable", "a"))
        self.assertIn("Rule A", self.md.read_text(encoding="utf-8"))

    def test_enable_in_order_disable_and_reorder(self):
        memory.run(ns("enable", "b"))
        memory.run(ns("enable", "a"))
        text = self.md.read_text(encoding="utf-8")
        self.assertLess(text.index("Rule B"), text.index("Rule A"))
        memory.run(ns("order", "a", "b"))
        text = self.md.read_text(encoding="utf-8")
        self.assertLess(text.index("Rule A"), text.index("Rule B"))
        memory.run(ns("disable", "a"))
        self.assertNotIn("Rule A", self.md.read_text(encoding="utf-8"))
        memory.run(ns("disable", "b"))
        self.assertEqual(self.md.read_text(encoding="utf-8"), "")
        self.assertEqual(state.load()["memory"], [])

    def test_order_must_list_exactly_the_enabled_snippets(self):
        memory.run(ns("enable", "a"))
        for names in (["a", "b"], []):
            with self.assertRaises(StandError):
                memory.run(ns("order", *names))

    def test_enable_twice_and_disable_when_off_change_nothing(self):
        memory.run(ns("enable", "a"))
        before = self.md.read_bytes()
        self.assertIn("already", memory.run(ns("enable", "a")).message)
        self.assertEqual(self.md.read_bytes(), before)
        self.assertIn("not enabled", memory.run(ns("disable", "b")).message)

    def test_dry_run_shows_a_diff_and_writes_nothing(self):
        self.md.write_text("mine\n", encoding="utf-8")
        result = memory.run(ns("enable", "a", dry_run=True))
        self.assertIn("Dry run", result.message)
        self.assertTrue(any("Rule A" in l for l in result.lines))
        self.assertEqual(self.md.read_text(encoding="utf-8"), "mine\n")
        self.assertEqual(state.load()["memory"], [])

    def test_half_markers_in_claude_md_stop_everything(self):
        self.md.write_text(f"mine\n{START}\nbroken\n", encoding="utf-8")
        with self.assertRaises(StandError):
            memory.run(ns("enable", "a"))
        self.assertEqual(self.md.read_text(encoding="utf-8"), f"mine\n{START}\nbroken\n")
        self.assertEqual(state.load()["memory"], [])

    def test_update_of_an_enabled_snippet_needs_apply_to_reach_claude_md(self):
        memory.run(ns("enable", "a"))
        new = self.tmp / "new.md"
        new.write_text("Rule A v2\n", encoding="utf-8")
        result = memory.run(ns("update", "a", file=str(new)))
        self.assertIn("apply", result.message)
        self.assertNotIn("v2", self.md.read_text(encoding="utf-8"))
        memory.run(ns("apply"))
        self.assertIn("Rule A v2", self.md.read_text(encoding="utf-8"))

    def test_delete_of_an_enabled_snippet_is_refused(self):
        memory.run(ns("enable", "a"))
        with self.assertRaises(StandError) as caught:
            memory.run(ns("delete", "a"))
        self.assertIn("disable", str(caught.exception))
        memory.run(ns("delete", "b"))
        self.assertFalse((self.data / "memory" / "b.md").exists())

    def test_enabled_follows_the_real_file_after_a_restore(self):
        self.md.write_text("mine\n", encoding="utf-8")
        memory.run(ns("enable", "a"))
        self.assertEqual(memory.enabled(), ["a"])
        files.restore(files.list_backups()[0]["name"])
        self.assertEqual(state.load()["memory"], ["a"])       # stale on purpose
        self.assertEqual(memory.enabled(), [])                # the real file has no block

    def test_restore_to_an_earlier_set_shows_the_real_enabled_list(self):
        self.md.write_text("mine\n", encoding="utf-8")
        memory.run(ns("enable", "a"))
        memory.run(ns("enable", "b"))
        files.restore(files.list_backups()[0]["name"])
        self.assertEqual(memory.enabled(), ["a"])
        marks = {r["name"]: r["active"] for r in memory.run(ns("list")).data}
        self.assertEqual((marks["a"], marks["b"]), (True, False))

    def test_snippets_named_like_a_marker_are_refused(self):
        path = self.tmp / "x.md"
        path.write_text("Rule\n", encoding="utf-8")
        for name in ("start", "end"):
            with self.assertRaises(StandError):
                memory.run(ns("create", name, file=str(path)))

    def test_snippets_with_stand_markers_or_no_text_are_refused(self):
        for text in ("", "  \n", "before <!-- stand:start --> after"):
            path = self.tmp / "bad.md"
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(StandError):
                memory.run(ns("create", "bad", file=str(path)))

    def test_create_from_example_show_check_list(self):
        (self.examples / "memory").mkdir()
        (self.examples / "memory" / "sample.md").write_text("Sample rule\n", encoding="utf-8")
        memory.run(ns("create", "mine", from_="sample"))
        self.assertIn("Sample rule", "\n".join(memory.run(ns("show", "mine")).lines))
        self.assertTrue(memory.run(ns("check")).ok)
        names = {r["name"] for r in memory.run(ns("list")).data}
        self.assertEqual(names, {"a", "b", "c", "mine", "sample"})

    def test_a_missing_enabled_snippet_is_a_clear_error(self):
        memory.run(ns("enable", "a"))
        (self.data / "memory" / "a.md").unlink()
        with self.assertRaises(StandError):
            memory.run(ns("apply"))

    def test_unknown_action(self):
        with self.assertRaises(StandError):
            memory.run(ns("explode"))


if __name__ == "__main__":
    unittest.main()
