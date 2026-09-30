import json
import unittest

from stand_helpers import StandCase, ns, sample_theme
from engine import StandError, files, state, theme


def add_example(case, name, display="Example Theme"):
    """Put a saved theme into the examples folder, the way a shipped example looks."""
    folder = case.examples / "themes" / name
    for filename, text in theme.item_files(theme.normalize(sample_theme(display))).items():
        (folder / filename).parent.mkdir(parents=True, exist_ok=True)
        (folder / filename).write_text(text, encoding="utf-8")


class RulesTest(StandCase):
    def test_a_valid_draft_has_no_problems_once_normalized(self):
        self.assertEqual(theme.problems(theme.normalize(sample_theme())), [])

    def test_normalize_adds_five_plugin_tips_first_and_keeps_facts(self):
        tips = theme.normalize(sample_theme())["tips"]
        self.assertEqual(len(tips), 20)
        self.assertEqual(tips[:5], theme.plugin_tips("Star Wars"))
        self.assertEqual(tips[5:], [f"Fact {i}" for i in range(15)])
        self.assertTrue(all(len(t) <= 90 for t in tips))

    def test_normalize_swaps_old_plugin_tips_for_fresh_ones(self):
        old = ["Subagents get Movies names. Check the task list.",
               "Run /tovar-themes-movies:off to put these settings back the way they were.",
               "Every theme setting lives in its plugin folder, not scattered in settings.json.",
               "/tovar-themes-movies:on backs up your settings before it changes anything.",
               "Turning on another theme turns this one off."]
        draft = sample_theme("Star Wars", tips=old + [f"Fact {i}" for i in range(15)])
        tips = theme.normalize(draft)["tips"]
        self.assertEqual(tips[:5], theme.plugin_tips("Star Wars"))
        self.assertEqual(len(tips), 20)

    def test_problems_lists_every_broken_rule(self):
        broken = theme.normalize(sample_theme(
            tipsLabel=" ", verbs=["a" * 31] + ["v"] * 38, names=["Neo", "Neo"], announcements=[""] * 20))
        text = "\n".join(theme.problems(broken))
        self.assertIn("tipsLabel is empty", text)
        self.assertIn("verbs: needs 40, has 39", text)
        self.assertIn("verbs: longer than 30", text)
        self.assertIn("verbs: repeated: v", text)
        self.assertIn("names: needs at least 100, has 2", text)
        self.assertIn("names: repeated: Neo", text)
        self.assertIn("announcements: every item must be non-empty text", text)


class CreateTest(StandCase):
    def create(self, name="star-wars", **options):
        return theme.run(ns("create", name, file=str(self.draft()), **options))

    def test_create_saves_three_files_with_plugin_tips(self):
        result = self.create()
        folder = self.data / "themes" / "star-wars"
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ["extras.json", "settings.json", "tips.json"])
        saved = theme.read_theme(folder)
        self.assertEqual(saved["display"], "Star Wars")
        self.assertEqual(len(saved["tips"]), 20)
        settings = self.read_json(folder / "settings.json")
        self.assertEqual(settings["spinnerTipsOverride"], {"tipsFile": "tips.json", "label": "Holocron"})
        self.assertEqual(settings["spinnerVerbs"]["mode"], "replace")
        self.assertIn("Saved theme 'star-wars'", result.message)

    def test_create_refuses_a_taken_name_and_bad_names(self):
        self.create()
        with self.assertRaises(StandError):
            self.create()
        with self.assertRaises(StandError):
            self.create("Bad Name")

    def test_create_with_problems_saves_nothing_and_lists_them(self):
        path = self.draft(sample_theme(names=["Neo"]), name="short.json")
        with self.assertRaises(StandError) as caught:
            theme.run(ns("create", "thin", file=str(path)))
        self.assertIn("names: needs at least 100, has 1", str(caught.exception))
        self.assertFalse((self.data / "themes" / "thin").exists())

    def test_create_needs_a_source_and_refuses_two(self):
        with self.assertRaises(StandError):
            theme.run(ns("create", "x"))
        with self.assertRaises(StandError):
            theme.run(ns("create", "x", file=str(self.draft()), from_="star-wars"))

    def test_create_from_an_example_copies_it(self):
        add_example(self, "movies", "Movies")
        theme.run(ns("create", "my-movies", from_="movies"))
        self.assertEqual(theme.read_theme(self.data / "themes" / "my-movies")["display"], "Movies")

    def test_create_dry_run_writes_nothing(self):
        result = self.create(dry_run=True)
        self.assertIn("Dry run", result.message)
        self.assertFalse((self.data / "themes").exists())

    def test_create_takes_a_theme_folder_a_settings_file_and_a_theme_json(self):
        self.create()
        folder = self.data / "themes" / "star-wars"
        theme.run(ns("create", "from-folder", file=str(folder)))
        theme.run(ns("create", "from-settings", file=str(folder / "settings.json")))
        as_json = self.tmp / "theme.json"
        as_json.write_text(json.dumps(sample_theme("Loose")), encoding="utf-8")
        theme.run(ns("create", "from-json", file=str(as_json)))
        for name in ("from-folder", "from-settings"):
            self.assertEqual(theme.read_theme(self.data / "themes" / name)["names"][0], "Name 0")
        self.assertEqual(theme.read_theme(self.data / "themes" / "from-json")["display"], "Loose")

    def test_a_settings_file_without_names_is_reported_not_half_saved(self):
        self.create()
        lone = self.tmp / "lone"
        lone.mkdir()
        for name in ("settings.json", "tips.json"):
            (lone / name).write_text((self.data / "themes" / "star-wars" / name).read_text(encoding="utf-8"), encoding="utf-8")
        with self.assertRaises(StandError) as caught:
            theme.run(ns("create", "no-names", file=str(lone)))
        self.assertIn("names: needs at least 100, has 0", str(caught.exception))
        self.assertFalse((self.data / "themes" / "no-names").exists())

    def test_accents_survive_create_read_and_export(self):
        names = [f"Pokémon {i}" for i in range(100)]
        path = self.draft(sample_theme("Pokémon", names=names), name="poke.json")
        theme.run(ns("create", "poke", file=str(path)))
        self.assertEqual(theme.read_theme(self.data / "themes" / "poke")["names"][0], "Pokémon 0")
        theme.run(ns("export", "poke", to=str(self.tmp / "out")))
        self.assertIn("Pokémon", (self.tmp / "out" / "extras.json").read_text(encoding="utf-8"))


class ChangeTest(StandCase):
    def setUp(self):
        super().setUp()
        theme.run(ns("create", "mine", file=str(self.draft())))
        add_example(self, "movies", "Movies")

    def test_update_replaces_your_theme_and_backs_up(self):
        newer = self.draft(sample_theme("Renamed"), name="new.json")
        result = theme.run(ns("update", "mine", file=str(newer)))
        self.assertEqual(theme.read_theme(self.data / "themes" / "mine")["display"], "Renamed")
        self.assertIn("Backup:", result.lines[-1])

    def test_update_refuses_examples(self):
        with self.assertRaises(StandError):
            theme.run(ns("update", "movies", file=str(self.draft())))

    @unittest.expectedFailure
    def test_update_of_the_active_theme_says_to_apply_again(self):
        st = state.load()
        st["theme"] = "mine"
        state.save(st)
        # active_name() reads the real settings (Task 5), so mark it active the same way here.
        settings = {"spinnerTipsOverride": {"tipsFile": str(self.data / "active" / "theme" / "tips.json")}}
        (self.config / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
        result = theme.run(ns("update", "mine", file=str(self.draft(sample_theme("Again"), name="a.json"))))
        self.assertIn("apply", result.message)

    def test_delete_removes_yours_and_refuses_examples(self):
        theme.run(ns("delete", "mine"))
        self.assertFalse((self.data / "themes" / "mine").exists())
        with self.assertRaises(StandError):
            theme.run(ns("delete", "movies"))

    @unittest.expectedFailure
    def test_delete_of_the_active_theme_is_refused(self):
        st = state.load()
        st["theme"] = "mine"
        state.save(st)
        settings = {"spinnerTipsOverride": {"tipsFile": str(self.data / "active" / "theme" / "tips.json")}}
        (self.config / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
        with self.assertRaises(StandError) as caught:
            theme.run(ns("delete", "mine"))
        self.assertIn("turn it off", str(caught.exception))
        self.assertTrue((self.data / "themes" / "mine").exists())


class ReadShowCheckExportTest(StandCase):
    def setUp(self):
        super().setUp()
        theme.run(ns("create", "mine", file=str(self.draft())))

    def test_read_prints_any_source_as_json_and_writes_nothing(self):
        result = theme.run(ns("read", str(self.data / "themes" / "mine")))
        self.assertEqual(result.data["display"], "Star Wars")
        self.assertEqual(json.loads(result.lines[0])["tipsLabel"], "Holocron")

    def test_read_of_a_bad_source_explains(self):
        with self.assertRaises(StandError):
            theme.run(ns("read", str(self.tmp / "missing")))
        junk = self.tmp / "junk.json"
        junk.write_text('{"a": 1}', encoding="utf-8")
        with self.assertRaises(StandError):
            theme.run(ns("read", str(junk)))

    def test_show_summarises(self):
        result = theme.run(ns("show", "mine"))
        self.assertIn("Star Wars", result.message)
        self.assertTrue(any(l.startswith("verbs: 40") for l in result.lines))

    def test_check_passes_and_fails(self):
        self.assertTrue(theme.run(ns("check")).ok)
        path = self.data / "themes" / "mine" / "extras.json"
        path.write_text(json.dumps({"display": "X", "names": ["a"]}), encoding="utf-8")
        result = theme.run(ns("check", "mine"))
        self.assertFalse(result.ok)
        self.assertIn("names: needs at least 100, has 1", "\n".join(result.lines))

    def test_export_writes_a_portable_folder_and_refuses_a_full_one(self):
        theme.run(ns("export", "mine", to=str(self.tmp / "out")))
        self.assertEqual(theme.read_theme(self.tmp / "out")["display"], "Star Wars")
        with self.assertRaises(StandError):
            theme.run(ns("export", "mine", to=str(self.tmp / "out")))
        with self.assertRaises(StandError):
            theme.run(ns("export", "mine"))

    def test_list_marks_yours_and_examples(self):
        add_example(self, "movies", "Movies")
        result = theme.run(ns("list"))
        self.assertEqual({r["name"]: r["source"] for r in result.data}, {"mine": "yours", "movies": "example"})

    def test_unknown_action_is_a_clear_error(self):
        with self.assertRaises(StandError) as caught:
            theme.run(ns("explode", "x"))
        self.assertIn("Unknown theme action", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
