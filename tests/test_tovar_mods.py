import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

ROSTER = """import type { Roster } from '../../hooks/character'

export const ROSTER: Roster = {
  calm: [{ name: 'Impa', thinks: ['keeping watch'] }],
  working: [{ name: 'Link' }, { name: "Kaepora Gaebora" }],
  burning: [{ name: 'Ganondorf' }],
}
"""

PROFILE = "# {name}\n\n- **Emoji:** 🗡️\n- **Color:** #2e9e44 (green)\n- **Speaks:** yes\n"


class ModsTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "root"
        shutil.copytree(REPO / "tovar-bar-template", self.root / "tovar-bar-template")
        shutil.copytree(REPO / "tools", self.root / "tools",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(REPO / "tovar-core" / "scripts", self.root / "tovar-core" / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__"))
        plugin = self.root / "tovar-mods"
        (plugin / "bars").mkdir(parents=True)
        (plugin / "hooks").mkdir()
        shutil.copy(REPO / "tovar-mods" / "hooks" / "narration.ts", plugin / "hooks" / "narration.ts")
        shutil.copy(REPO / "tovar-mods" / "hooks" / "character.ts", plugin / "hooks" / "character.ts")
        (plugin / "hooks" / "bars.ts").write_text("", encoding="utf-8")
        (plugin / ".claude-plugin").mkdir()
        manifest = json.loads((REPO / "tovar-mods" / ".claude-plugin" / "plugin.json").read_text())
        manifest["userConfig"]["bar"]["options"] = ["off"]
        (plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
        (self.root / ".claude-plugin").mkdir()
        self.write_market([])

    def write_market(self, plugins):
        (self.root / ".claude-plugin" / "marketplace.json").write_text(
            json.dumps({"name": "test-market", "owner": {"name": "Test"}, "plugins": plugins}),
            encoding="utf-8",
        )

    def market(self):
        path = self.root / ".claude-plugin" / "marketplace.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def run_mods(self, *args):
        env = {**os.environ, "TOVAR_MODS_SKIP_CHECKS": "1"}
        return subprocess.run(
            [sys.executable, str(self.root / "tools" / "tovar-mods.py"), *args],
            capture_output=True, text=True, env=env,
        )

    def bar(self, name):
        return self.root / "tovar-mods" / "bars" / name

    def bars_ts(self):
        return (self.root / "tovar-mods" / "hooks" / "bars.ts").read_text(encoding="utf-8")

    def options(self):
        path = self.root / "tovar-mods" / ".claude-plugin" / "plugin.json"
        return json.loads(path.read_text(encoding="utf-8"))["userConfig"]["bar"]["options"]

    def finish(self, name):
        """Swap the template's examples for a real three-mood roster."""
        bar = self.bar(name)
        (bar / "roster.ts").write_text(ROSTER, encoding="utf-8")
        for f in (bar / "characters").glob("*.md"):
            f.unlink()
        for file, title in (("impa", "Impa"), ("link", "Link"),
                            ("kaepora-gaebora", "Kaepora Gaebora"), ("ganondorf", "Ganondorf")):
            (bar / "characters" / f"{file}.md").write_text(
                PROFILE.format(name=title), encoding="utf-8"
            )


class NewBarTest(ModsTestCase):
    def test_new_copies_the_template_into_the_bars_folder(self):
        r = self.run_mods("new", "zelda")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.bar("zelda") / "roster.ts").is_file())
        self.assertTrue((self.bar("zelda") / "characters" / "idle-example.md").is_file())
        self.assertFalse((self.bar("zelda") / "hooks").exists())
        self.assertFalse((self.root / "mods").exists())

    def test_new_adds_the_bar_to_the_list_and_the_setting(self):
        self.run_mods("new", "zelda")
        self.run_mods("new", "star-fox")
        bars = self.bars_ts()
        self.assertIn("import { ROSTER as bar1 } from '../bars/zelda/roster'", bars)
        self.assertIn("import { ROSTER as bar0 } from '../bars/star-fox/roster'", bars)
        self.assertIn("'zelda': bar1,", bars)
        self.assertIn("'star-fox': bar0,", bars)
        self.assertEqual(self.options(), ["star-fox", "zelda", "off"])

    def test_the_generated_list_has_the_shape_the_plugin_expects(self):
        self.run_mods("new", "zelda")
        self.assertEqual(self.bars_ts(), (
            "// Every bar, by the name the Bar setting uses. Written by tools/tovar-mods.py.\n"
            "import type { Roster } from './character'\n"
            "import { ROSTER as bar0 } from '../bars/zelda/roster'\n"
            "\n"
            "export const BARS: Record<string, Roster> = {\n"
            "  'zelda': bar0,\n"
            "}\n"
        ))

    def test_awkward_names_get_unique_safe_identifiers(self):
        names = ["a-1", "a1", "2048", "class", "new", "default"]
        for n in names:
            self.assertEqual(self.run_mods("new", n).returncode, 0, n)
        bars = self.bars_ts()
        idents = re.findall(r"ROSTER as (\S+) }", bars)
        self.assertEqual(len(idents), len(names))
        self.assertEqual(len(set(idents)), len(names))
        for i in idents:
            self.assertRegex(i, r"^bar\d+$")
        for n in names:
            self.assertRegex(bars, rf"'{n}': bar\d+,")
        self.assertEqual(self.options(), sorted(names) + ["off"])

    def test_regenerating_leaves_the_plugin_manifest_style_alone(self):
        manifest = self.root / "tovar-mods" / ".claude-plugin" / "plugin.json"
        shutil.copy(REPO / "tovar-mods" / ".claude-plugin" / "plugin.json", manifest)
        self.run_mods("new", "zelda")
        self.run_mods("new", "zelda2")
        text = manifest.read_text(encoding="utf-8")
        self.assertIn('"author": { "name": "Jose Tovar" }', text)
        self.assertIn('"options": ["zelda", "zelda2", "off"]', text)
        self.assertEqual(json.loads(text)["userConfig"]["bar"]["options"], ["zelda", "zelda2", "off"])

    def test_new_does_not_touch_the_marketplace(self):
        self.run_mods("new", "zelda")
        self.assertEqual(self.market()["plugins"], [])

    def test_new_refuses_off_a_bad_name_or_an_existing_bar(self):
        self.assertNotEqual(self.run_mods("new", "off").returncode, 0)
        self.assertNotEqual(self.run_mods("new", "Bad Name").returncode, 0)
        self.assertFalse(self.bar("off").exists())
        self.run_mods("new", "zelda")
        r = self.run_mods("new", "zelda")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("already exists", r.stderr)


class CheckBarTest(ModsTestCase):
    def test_check_flags_the_template_examples(self):
        self.run_mods("new", "zelda")
        r = self.run_mods("check", "zelda")
        self.assertEqual(r.returncode, 1)
        self.assertIn("roster.ts still has the TODO line", r.stdout)
        self.assertIn("idle-example.md still has the TODO line", r.stdout)

    def test_check_passes_a_finished_bar(self):
        self.run_mods("new", "zelda")
        self.finish("zelda")
        r = self.run_mods("check", "zelda")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("zelda: OK", r.stdout)

    def test_check_flags_missing_and_stray_profiles(self):
        self.run_mods("new", "zelda")
        self.finish("zelda")
        (self.bar("zelda") / "characters" / "link.md").unlink()
        (self.bar("zelda") / "characters" / "navi.md").write_text("hey", encoding="utf-8")
        r = self.run_mods("check", "zelda")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Link: no profile at characters/link.md", r.stdout)
        self.assertIn("characters/navi.md belongs to no character", r.stdout)

    def test_check_flags_a_profile_without_color(self):
        self.run_mods("new", "zelda")
        self.finish("zelda")
        (self.bar("zelda") / "characters" / "impa.md").write_text(
            "# Impa\n\n- **Emoji:** 🥷\n- **Speaks:** yes\n", encoding="utf-8"
        )
        r = self.run_mods("check", "zelda")
        self.assertIn("impa.md: missing the Color (#rrggbb) line", r.stdout)

    def test_check_flags_an_empty_mood(self):
        self.run_mods("new", "zelda")
        self.finish("zelda")
        roster = self.bar("zelda") / "roster.ts"
        roster.write_text(
            roster.read_text().replace("burning: [{ name: 'Ganondorf' }]", "burning: []")
        )
        (self.bar("zelda") / "characters" / "ganondorf.md").unlink()
        r = self.run_mods("check", "zelda")
        self.assertIn("burning has no characters", r.stdout)


    def test_check_flags_a_profile_without_emoji_or_speaks(self):
        self.run_mods("new", "zelda")
        self.finish("zelda")
        (self.bar("zelda") / "characters" / "impa.md").write_text(
            "# Impa\n\n- **Color:** #2e9e44\n- **Speaks:** yes\n", encoding="utf-8")
        (self.bar("zelda") / "characters" / "link.md").write_text(
            "# Link\n\n- **Emoji:** 🗡️\n- **Color:** #2e9e44\n", encoding="utf-8")
        r = self.run_mods("check", "zelda")
        self.assertIn("impa.md: missing the Emoji line", r.stdout)
        self.assertIn("link.md: missing the Speaks line", r.stdout)

    def test_check_flags_a_bar_missing_from_the_list_or_the_setting(self):
        self.run_mods("new", "zelda")
        self.finish("zelda")
        (self.root / "tovar-mods" / "hooks" / "bars.ts").write_text("", encoding="utf-8")
        manifest = self.root / "tovar-mods" / ".claude-plugin" / "plugin.json"
        data = json.loads(manifest.read_text())
        data["userConfig"]["bar"]["options"] = ["off"]
        manifest.write_text(json.dumps(data))
        r = self.run_mods("check", "zelda")
        self.assertEqual(r.returncode, 1)
        self.assertIn("missing from hooks/bars.ts", r.stdout)
        self.assertIn("missing from the Bar setting", r.stdout)

    def test_check_with_no_names_checks_every_bar(self):
        self.run_mods("new", "zelda")
        self.finish("zelda")
        r = self.run_mods("check")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("zelda: OK", r.stdout)

    def test_check_with_an_unknown_bar_fails(self):
        r = self.run_mods("check", "nope")
        self.assertEqual(r.returncode, 1)
        self.assertIn("nope: not found", r.stdout)


class RosterParsingTest(ModsTestCase):
    def test_a_bracket_inside_a_quoted_thinking_action_does_not_cut_the_list(self):
        self.run_mods("new", "zelda")
        self.finish("zelda")
        (self.bar("zelda") / "roster.ts").write_text(ROSTER.replace(
            "['keeping watch']", "['reading [the map] closely', \"it's ] odd\", 'watching']"
        ), encoding="utf-8")
        draft = self.root / "draft.json"
        verbs = ["Watching"] + [f"Doing chore {i}" for i in range(39)]
        draft.write_text(json.dumps({
            "display": "T", "tipsLabel": "Fact", "verbs": verbs,
            "announcements": [f"L{i}" for i in range(20)], "tips": [f"F{i}" for i in range(15)],
            "names": [f"H{i}" for i in range(100)]}), encoding="utf-8")
        subprocess.run([sys.executable, str(self.root / "tovar-core" / "scripts" / "tovar.py"),
                        "--data", str(self.root / "data"), "theme", "create", "test",
                        "--file", str(draft)], capture_output=True, text=True, check=True)
        r = self.run_mods("overlap", "zelda", "test", "--data", str(self.root / "data"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn('"Watching" is also a thinking action of Impa', r.stdout)


class RegisterPluginTest(ModsTestCase):
    def hand_made(self, name):
        manifest = self.root / name / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"name": name}), encoding="utf-8")

    def test_register_lists_a_hand_made_plugin_once(self):
        self.hand_made("tovar-clock")
        r = self.run_mods("register", "tovar-clock", "A clock above the prompt.")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_mods("register", "tovar-clock", "A clock above the prompt.")
        self.assertIn("already listed", r.stdout)
        plugins = self.market()["plugins"]
        self.assertEqual([p["name"] for p in plugins], ["tovar-clock"])
        self.assertEqual(plugins[0]["source"], "./tovar-clock")

    def test_register_refuses_a_name_without_the_tovar_prefix(self):
        self.hand_made("clock")
        r = self.run_mods("register", "clock", "A clock above the prompt.")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("tovar-", r.stderr)
        self.assertEqual(self.market()["plugins"], [])

    def test_register_refuses_a_folder_without_a_manifest(self):
        (self.root / "tovar-empty").mkdir()
        r = self.run_mods("register", "tovar-empty", "Nothing here.")
        self.assertNotEqual(r.returncode, 0)



def theme_draft(verbs):
    return {
        "display": "Test",
        "tipsLabel": "Fact",
        "verbs": verbs + [f"Doing chore {i}" for i in range(40 - len(verbs))],
        "announcements": [f"Line {i}" for i in range(20)],
        "tips": [f"Fact {i}" for i in range(15)],
        "names": [f"Hero {i}" for i in range(100)],
    }


class OverlapTest(ModsTestCase):
    def make_theme(self, verbs):
        draft = self.root / "draft.json"
        draft.write_text(json.dumps(theme_draft(verbs)), encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(self.root / "tovar-core" / "scripts" / "tovar.py"),
             "--data", str(self.root / "data"), "theme", "create", "test", "--file", str(draft)],
            capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def overlap(self):
        return self.run_mods("overlap", "zelda", "test", "--data", str(self.root / "data"))

    def setUp(self):
        super().setUp()
        self.run_mods("new", "zelda")
        self.finish("zelda")

    def test_overlap_passes_a_theme_that_repeats_nothing(self):
        self.make_theme(["Opening a chest", "Rolling past a Deku Scrub"])
        r = self.overlap()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("zelda vs theme test: OK", r.stdout)

    def test_overlap_flags_a_verb_that_names_a_bar_character(self):
        self.make_theme(["Link is opening a chest", "Linking the files"])
        r = self.overlap()
        self.assertEqual(r.returncode, 1)
        self.assertIn('"Link is opening a chest" names Link', r.stdout)
        self.assertNotIn("Linking the files", r.stdout)

    def test_overlap_flags_a_verb_equal_to_a_thinking_action(self):
        self.make_theme(["Keeping watch…"])
        r = self.overlap()
        self.assertEqual(r.returncode, 1)
        self.assertIn('"Keeping watch…" is also a thinking action of Impa', r.stdout)

    def test_overlap_counts_generic_thinking_for_characters_without_their_own(self):
        self.make_theme(["Pondering"])
        r = self.overlap()
        self.assertEqual(r.returncode, 1)
        self.assertIn('"Pondering" is also a thinking action of', r.stdout)
        self.assertIn("Ganondorf", r.stdout)

    def test_overlap_flags_an_unknown_bar(self):
        self.make_theme(["Opening a chest"])
        r = self.run_mods("overlap", "nope", "test", "--data", str(self.root / "data"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("nope", r.stderr)

    def test_overlap_flags_an_unknown_theme(self):
        r = self.run_mods("overlap", "zelda", "missing", "--data", str(self.root / "data"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Could not read theme 'missing'", r.stderr)


class ScriptUsageTest(ModsTestCase):
    def test_no_command_or_an_unknown_one_prints_the_usage(self):
        for args in ((), ("explode",)):
            r = self.run_mods(*args)
            self.assertNotEqual(r.returncode, 0, args)
            self.assertIn("new <bar>", r.stderr)

    def test_each_command_explains_wrong_arguments(self):
        for args, usage in ((("new",), "usage: tovar-mods.py new"),
                            (("new", "a", "b"), "usage: tovar-mods.py new"),
                            (("register", "tovar-x"), "usage: tovar-mods.py register"),
                            (("overlap", "zelda"), "usage: tovar-mods.py overlap"),
                            (("overlap", "zelda", "t", "--data"), "usage: tovar-mods.py overlap")):
            r = self.run_mods(*args)
            self.assertNotEqual(r.returncode, 0, args)
            self.assertIn(usage, r.stderr)

    def test_check_with_no_bars_says_so(self):
        r = self.run_mods("check")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("No bars found.", r.stderr)


class CheckMoreTest(ModsTestCase):
    def setUp(self):
        super().setUp()
        self.run_mods("new", "zelda")
        self.finish("zelda")

    def test_check_flags_a_character_in_two_moods(self):
        roster = self.bar("zelda") / "roster.ts"
        roster.write_text(roster.read_text().replace("burning: [{ name: 'Ganondorf' }]",
                                                     "burning: [{ name: 'Ganondorf' }, { name: 'Link' }]"))
        r = self.run_mods("check", "zelda")
        self.assertEqual(r.returncode, 1)
        self.assertIn("roster.ts: repeated: Link", r.stdout)

    def test_check_flags_a_profile_still_holding_the_todo_line(self):
        profile = self.bar("zelda") / "characters" / "impa.md"
        profile.write_text(profile.read_text() + "\nTODO(tovar-new-bar)\n", encoding="utf-8")
        r = self.run_mods("check", "zelda")
        self.assertEqual(r.returncode, 1)
        self.assertIn("characters/impa.md still has the TODO line", r.stdout)

    def test_check_without_claude_on_the_path_says_the_plugin_checks_did_not_run(self):
        env = {k: v for k, v in os.environ.items() if k != "TOVAR_MODS_SKIP_CHECKS"}
        env["PATH"] = ""
        r = subprocess.run([sys.executable, str(self.root / "tools" / "tovar-mods.py"), "check", "zelda"],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 1)
        self.assertIn("zelda: OK", r.stdout)
        self.assertIn("claude is not on PATH", r.stdout)


if __name__ == "__main__":
    unittest.main()
