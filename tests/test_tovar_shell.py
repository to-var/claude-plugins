import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tovar_helpers import REPO

SHELL = REPO / "tovar-shell"
sys.path.insert(0, str(SHELL / "scripts"))
import tovar_shell  # noqa: E402

SKILL = (SHELL / "skills" / "tmux" / "SKILL.md").read_text(encoding="utf-8")
EXAMPLE_THEMES = [p.name for p in (REPO / "tovar-core" / "examples" / "themes").iterdir()]


class ShellCase(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        self.home, self.data, self.config = self.tmp / "home", self.tmp / "data", self.tmp / "config"
        for folder in (self.home, self.data, self.config):
            folder.mkdir()
        patch = mock.patch.dict(os.environ, {
            "HOME": str(self.home), "CLAUDE_PLUGIN_DATA": str(self.data),
            "CLAUDE_CONFIG_DIR": str(self.config)})
        patch.start()
        self.addCleanup(patch.stop)
        os.environ.pop("TOVAR_STATE", None)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SHELL / "scripts" / "tovar_shell.py"), *args],
                              capture_output=True, text=True, env=os.environ)

    def set_theme(self, name):
        folder = self.config / "plugins" / "data" / "tovar-core-tovar"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "state.json").write_text(json.dumps({"theme": name}), encoding="utf-8")

    def skin(self, **changes):
        data = json.loads((SHELL / "tmux" / "skins" / "default.json").read_text(encoding="utf-8"))
        for key, value in changes.items():
            part, _, field = key.partition("__")
            if field:
                data[part][field] = value
            else:
                data[part] = value
        return data


class SkinFilesTest(ShellCase):
    def test_every_shipped_skin_is_valid(self):
        for path in sorted((SHELL / "tmux" / "skins").glob("*.json")):
            skin = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(tovar_shell.problems(skin), [], path.name)

    def test_every_example_theme_has_a_skin_and_default_exists(self):
        names = {p.stem for p in (SHELL / "tmux" / "skins").glob("*.json")}
        self.assertIn("default", names)
        for theme in EXAMPLE_THEMES:
            self.assertIn(theme, names)

    def test_skin_problems_are_reported(self):
        self.assertIn("menu.layout: one of buttons, list", tovar_shell.problems(self.skin(menu__layout="grid")))
        self.assertTrue(any("colors.bg" in p for p in tovar_shell.problems(self.skin(colors__bg=999))))
        self.assertTrue(any("title_format" in p for p in tovar_shell.problems(self.skin(menu__title_format="no braces"))))
        self.assertTrue(any("rule" in p for p in tovar_shell.problems(self.skin(menu__rule="=="))))


class ApplyTest(ShellCase):
    def test_apply_writes_config_menu_and_skin(self):
        done = self.run_cli("tmux", "apply", "pokemon")
        self.assertEqual(done.returncode, 0, done.stderr)
        conf = (self.home / ".tmux.conf").read_text(encoding="utf-8")
        self.assertTrue(conf.startswith(tovar_shell.MARKER))
        self.assertNotIn("{{", conf)
        folder = self.home / ".config" / "tmux" / "tovar"
        self.assertIn(str(folder), conf)
        for name in ("open.sh", "menu.py", "skin.json"):
            self.assertTrue((folder / name).is_file(), name)
        self.assertTrue(os.access(folder / "open.sh", os.X_OK))
        self.assertNotIn("{{", (folder / "open.sh").read_text(encoding="utf-8"))
        self.assertEqual(json.loads((self.data / "state.json").read_text())["tmux"]["skin"], "pokemon")

    def test_dry_run_writes_nothing(self):
        done = self.run_cli("tmux", "apply", "zelda", "--dry-run")
        self.assertEqual(done.returncode, 0)
        self.assertIn("Would write", done.stdout)
        self.assertFalse((self.home / ".tmux.conf").exists())
        self.assertFalse((self.data / "state.json").exists())

    def test_apply_without_a_name_follows_the_active_theme(self):
        self.set_theme("smash-bros")
        self.run_cli("tmux", "apply")
        self.assertEqual(json.loads((self.data / "state.json").read_text())["tmux"]["skin"], "smash-bros")

    def test_an_older_tovar_themes_plugin_is_found_in_settings(self):
        (self.config / "settings.json").write_text(json.dumps({"spinnerTipsOverride": {
            "tipsFile": "/home/x/.claude/tovar-themes/pokemon/tips.json"}}), encoding="utf-8")
        self.assertIn("Skin: pokemon", self.run_cli("tmux", "apply", "--dry-run").stdout)

    def test_a_theme_without_a_skin_gets_default(self):
        self.set_theme("star-wars")
        done = self.run_cli("tmux", "apply", "--dry-run")
        self.assertIn("Skin: default", done.stdout)
        self.assertIn("star-wars", done.stdout)

    def test_no_theme_gets_default(self):
        self.assertIn("Skin: default", self.run_cli("tmux", "apply", "--dry-run").stdout)

    def test_unknown_skin_is_an_error(self):
        done = self.run_cli("tmux", "apply", "nope")
        self.assertEqual(done.returncode, 1)
        self.assertIn("No skin named 'nope'", done.stderr)

    def test_your_own_skin_hides_an_example(self):
        (self.data / "skins").mkdir()
        (self.data / "skins" / "pokemon.json").write_text(
            json.dumps(self.skin(display="My Pokemon")), encoding="utf-8")
        self.run_cli("tmux", "apply", "pokemon")
        skin = json.loads((self.home / ".config/tmux/tovar/skin.json").read_text(encoding="utf-8"))
        self.assertEqual(skin["display"], "My Pokemon")

    def test_every_skin_renders_a_config_tmux_accepts(self):
        if not shutil.which("tmux"):
            self.skipTest("tmux is not installed")
        for path in sorted((SHELL / "tmux" / "skins").glob("*.json")):
            with self.subTest(skin=path.stem):
                self.run_cli("tmux", "apply", path.stem)
                sock = f"tovar-test-{os.getpid()}"
                done = subprocess.run(
                    ["tmux", "-L", sock, "-f", str(self.home / ".tmux.conf"), "start-server", ";",
                     "show", "-g", "prefix"], capture_output=True, text=True,
                    env={**os.environ, "HOME": str(self.home)})
                subprocess.run(["tmux", "-L", sock, "kill-server"], capture_output=True)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(done.stderr, "")


class BackupAndOffTest(ShellCase):
    def test_existing_config_is_saved_and_off_restores_it(self):
        (self.home / ".tmux.conf").write_text("set -g mouse off\n", encoding="utf-8")
        self.run_cli("tmux", "apply", "pokemon")
        self.assertTrue(read_backup(self.data).startswith("set -g mouse off"))
        self.run_cli("tmux", "apply", "zelda")  # a second apply must not overwrite the backup
        self.assertTrue(read_backup(self.data).startswith("set -g mouse off"))
        done = self.run_cli("tmux", "off")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual((self.home / ".tmux.conf").read_text(encoding="utf-8"), "set -g mouse off\n")
        self.assertFalse((self.home / ".config" / "tmux" / "tovar").exists())
        self.assertNotIn("tmux", json.loads((self.data / "state.json").read_text()))

    def test_off_without_a_previous_config_removes_the_managed_one(self):
        self.run_cli("tmux", "apply", "pokemon")
        self.run_cli("tmux", "off")
        self.assertFalse((self.home / ".tmux.conf").exists())

    def test_off_leaves_a_config_that_is_not_ours(self):
        (self.home / ".tmux.conf").write_text("set -g mouse off\n", encoding="utf-8")
        done = self.run_cli("tmux", "off")
        self.assertIn("not managed by tovar-shell", done.stdout)
        self.assertEqual((self.home / ".tmux.conf").read_text(encoding="utf-8"), "set -g mouse off\n")


def read_backup(data):
    found = sorted((data / "backups").glob("*/tmux.conf"))
    return found[0].read_text(encoding="utf-8")


class ListStatusCreateTest(ShellCase):
    def test_list_marks_applied_and_theme_match(self):
        self.set_theme("zelda")
        self.run_cli("tmux", "apply", "pokemon")
        data = json.loads(self.run_cli("tmux", "list", "--json").stdout)
        rows = {r["name"]: r for r in data["skins"]}
        self.assertTrue(rows["pokemon"]["applied"])
        self.assertTrue(rows["zelda"]["matches_theme"])
        self.assertEqual(data["active_theme"], "zelda")

    def test_status_suggests_the_skin_for_the_theme(self):
        self.set_theme("movies")
        info = json.loads(self.run_cli("tmux", "status", "--json").stdout)
        self.assertEqual(info["suggested_skin"], "movies")
        self.assertFalse(info["managed"])

    def test_create_saves_a_valid_draft_and_rejects_a_bad_one(self):
        good = self.tmp / "good.json"
        good.write_text(json.dumps(self.skin(display="Star Wars")), encoding="utf-8")
        done = self.run_cli("tmux", "create", "star-wars", "--file", str(good))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((self.data / "skins" / "star-wars.json").is_file())
        self.assertIn("star-wars", self.run_cli("tmux", "list").stdout)
        bad = self.tmp / "bad.json"
        bad.write_text(json.dumps(self.skin(menu__layout="grid")), encoding="utf-8")
        done = self.run_cli("tmux", "create", "bad-one", "--file", str(bad))
        self.assertEqual(done.returncode, 1)
        self.assertFalse((self.data / "skins" / "bad-one.json").exists())

    def test_create_needs_a_clean_name(self):
        draft = self.tmp / "d.json"
        draft.write_text(json.dumps(self.skin()), encoding="utf-8")
        self.assertEqual(self.run_cli("tmux", "create", "Bad Name", "--file", str(draft)).returncode, 1)


class MenuTest(ShellCase):
    def test_menu_script_compiles(self):
        subprocess.run([sys.executable, "-m", "py_compile", str(SHELL / "tmux" / "menu.py")], check=True)


class SkillTest(unittest.TestCase):
    def test_skill_has_a_name_and_description(self):
        head = SKILL.split("---")[1]
        self.assertIn("name: tmux", head)
        self.assertIn("description:", head)

    def test_every_command_in_the_skill_is_a_real_action(self):
        import re
        actions = re.findall(r"tovar_shell\.py\"[^\n]*?\btmux ([a-z]+)", SKILL)
        self.assertTrue(actions)
        for action in actions:
            self.assertIn(action, tovar_shell.TMUX_ACTIONS)

    def test_skill_covers_every_action(self):
        for action in tovar_shell.TMUX_ACTIONS:
            self.assertRegex(SKILL, rf"tovar_shell\.py\"[^\n]*\btmux {action}\b", action)


if __name__ == "__main__":
    unittest.main()
