import re
import unittest

from stand_helpers import REPO
from engine import items

SKILLS = REPO / "stand" / "skills"
COMMAND = re.compile(r"stand\.py.*?\b(theme|style|memory)\s+([a-z-]+)")


def read(name):
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


class SkillsTest(unittest.TestCase):
    def test_every_skill_has_a_name_and_description(self):
        for name in ("theme", "style", "memory", "undo"):
            text = read(name)
            self.assertTrue(text.startswith("---\n"), name)
            head = text.split("---")[1]
            self.assertIn(f"name: {name}", head)
            self.assertIn("description:", head)

    def test_every_command_in_a_skill_is_a_real_action(self):
        for name in ("theme", "style", "memory", "undo"):
            for area, action in COMMAND.findall(read(name)):
                self.assertIn(action, items.ACTIONS[area], f"{name}: {area} {action}")

    def test_each_area_skill_mentions_every_action_of_its_area(self):
        for area in ("theme", "style", "memory"):
            text = read(area)
            for action in items.ACTIONS[area]:
                self.assertRegex(text, rf"stand\.py.*\b{area} {action}\b", f"{area} skill lacks '{action}'")

    def test_undo_covers_status_and_restore(self):
        text = read("undo")
        self.assertRegex(text, r"stand\.py.*\bstatus\b")
        self.assertRegex(text, r"stand\.py.*\brestore\b")

    def test_every_command_passes_the_data_folder(self):
        for name in ("theme", "style", "memory", "undo"):
            for line in read(name).splitlines():
                if "stand.py" in line and "--data" not in line:
                    self.fail(f"{name}: '{line.strip()}' lacks --data")

    def test_skills_never_tell_claude_to_edit_the_files_by_hand(self):
        for name in ("theme", "style", "memory", "undo"):
            self.assertIn("never edit", read(name).lower())

    def test_no_em_or_en_dashes(self):
        for path in list(SKILLS.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("\u2014", text, path)
            self.assertNotIn("\u2013", text, path)


if __name__ == "__main__":
    unittest.main()
