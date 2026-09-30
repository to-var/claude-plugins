import contextlib
import io
import json
import unittest
from unittest import mock

from stand_helpers import StandCase, sample_theme


class CliTest(StandCase):
    def test_create_apply_status_off_through_the_command_line(self):
        draft = self.draft()
        r = self.run_cli("theme", "create", "star-wars", "--file", str(draft))
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("theme", "apply", "star-wars", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Dry run", r.stdout)
        self.assertFalse((self.config / "settings.json").exists())
        r = self.run_cli("theme", "apply", "star-wars")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("status")
        self.assertIn("theme: star-wars", r.stdout)
        r = self.run_cli("theme", "off")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("theme: none", self.run_cli("status").stdout)

    def test_json_output_is_machine_readable(self):
        self.run_cli("theme", "create", "star-wars", "--file", str(self.draft()))
        r = self.run_cli("theme", "list", "--json")
        payload = json.loads(r.stdout)
        self.assertEqual(payload["data"][0]["name"], "star-wars")

    def test_errors_go_to_stderr_with_exit_code_one(self):
        r = self.run_cli("theme", "show", "nope")
        self.assertEqual(r.returncode, 1)
        self.assertIn("stand:", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_unknown_action_and_missing_name_are_clear_errors(self):
        r = self.run_cli("theme", "explode")
        self.assertEqual((r.returncode, "Unknown theme action" in r.stderr), (1, True))
        r = self.run_cli("theme", "show")
        self.assertEqual((r.returncode, "exactly one name" in r.stderr), (1, True))

    def test_failed_check_exits_one_and_still_prints(self):
        self.run_cli("theme", "create", "star-wars", "--file", str(self.draft()))
        (self.data / "themes" / "star-wars" / "extras.json").write_text('{"display": "X", "names": []}', encoding="utf-8")
        r = self.run_cli("theme", "check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("names: needs at least 100", r.stdout)

    def test_data_flag_replaces_the_environment(self):
        other = self.tmp / "other-data"
        r = self.run_cli("--data", str(other), "theme", "create", "x", "--file", str(self.draft()))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((other / "themes" / "x" / "settings.json").is_file())
        self.assertFalse((self.data / "themes").exists())

    def test_restore_lists_and_restores(self):
        self.run_cli("theme", "create", "star-wars", "--file", str(self.draft()))
        (self.config / "settings.json").write_text('{"model": "opus"}\n', encoding="utf-8")
        self.run_cli("theme", "apply", "star-wars")
        listing = self.run_cli("restore")
        self.assertEqual(listing.returncode, 0, listing.stderr)
        name = json.loads(self.run_cli("restore", "--json").stdout)["data"][0]["name"]
        r = self.run_cli("restore", name)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.settings(), {"model": "opus"})
        self.assertIn("theme: none", self.run_cli("status").stdout)

    def test_hook_prints_json_and_never_fails(self):
        self.run_cli("theme", "create", "star-wars", "--file", str(self.draft(sample_theme("Pokémon"))))
        self.run_cli("theme", "apply", "star-wars")
        event = json.dumps({"tool_input": {"description": "x"}})
        r = self.run_cli("--data", str(self.data), "hook", "name", stdin=event)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("updatedInput", r.stdout)
        r = self.run_cli("hook", "name", stdin="garbage")
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_hook_keeps_non_ascii_prompts_intact(self):
        self.run_cli("theme", "create", "star-wars", "--file", str(self.draft()))
        self.run_cli("theme", "apply", "star-wars")
        prompt = "Revisa la canci\u00f3n y el a\u00f1o \u20ac"
        event = json.dumps({"tool_input": {"prompt": prompt, "description": "x"}}, ensure_ascii=False)
        r = self.run_cli("hook", "name", stdin=event)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["hookSpecificOutput"]["updatedInput"]["prompt"], prompt)

    def test_a_file_error_is_reported_not_a_traceback(self):
        from engine import cli, files
        draft = self.draft()
        with mock.patch.object(files, "atomic_write", side_effect=PermissionError("locked")):
            with contextlib.redirect_stderr(io.StringIO()) as err:
                code = cli.main(["theme", "create", "x", "--file", str(draft)])
        self.assertEqual(code, 1)
        self.assertIn("stand:", err.getvalue())
        self.assertIn("locked", err.getvalue())

    def test_restore_warns_that_whole_files_are_replaced(self):
        self.run_cli("theme", "create", "star-wars", "--file", str(self.draft()))
        (self.config / "settings.json").write_text('{"model": "opus"}\n', encoding="utf-8")
        self.run_cli("theme", "apply", "star-wars")
        name = json.loads(self.run_cli("restore", "--json").stdout)["data"][0]["name"]
        r = self.run_cli("restore", name, "--dry-run")
        self.assertIn("whole file", r.stdout)

    def test_accents_print_without_crashing(self):
        names = [f"Pokémon {i}" for i in range(100)]
        self.run_cli("theme", "create", "poke", "--file", str(self.draft(sample_theme("Pokémon", names=names))))
        r = self.run_cli("theme", "show", "poke")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Pokémon", r.stdout)


if __name__ == "__main__":
    unittest.main()
