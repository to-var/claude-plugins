"""Repo-wide rules: no long dashes, no leftover old names, every name starts with tovar-."""
import json
import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OLD = "dnats"[::-1]
SKIP_DIRS = {".git", "__pycache__", "docs", "node_modules", ".superpowers"}
LEGACY = re.compile(
    rf"(?i)(?<![a-z]){OLD}(?![a-z])|{OLD}(error|case|_helpers|_examples)|{OLD}\.py|/{OLD}:"
)
PREFIX = "tovar-"


def checked(path):
    rel = path.relative_to(REPO)
    generated = ".claude-plugin" in rel.parts and "types" in rel.parts  # written by the engine
    return not SKIP_DIRS & set(rel.parts) and not generated


def tracked():
    """Every file git tracks or would track (untracked but not ignored)."""
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=REPO, check=True, capture_output=True,
    ).stdout.decode("utf-8")
    return [REPO / rel for rel in out.split("\0") if rel]


def files():
    """Every tracked text file: anything that decodes as UTF-8, binaries skipped."""
    for path in tracked():
        if not path.is_file() or not checked(path):
            continue
        try:
            text = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            continue
        yield path.relative_to(REPO), text


def listed_plugins():
    market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    return market["plugins"]


class NamesTest(unittest.TestCase):
    def test_no_long_dashes(self):
        for rel, text in files():
            self.assertNotIn("\u2014", text, rel)
            self.assertNotIn("\u2013", text, rel)

    def test_no_old_name_in_text(self):
        for rel, text in files():
            for n, line in enumerate(text.splitlines(), 1):
                self.assertIsNone(LEGACY.search(line), f"{rel}:{n}: {line.strip()}")

    def test_no_old_name_in_paths(self):
        for path in REPO.rglob("*"):
            if not checked(path):
                continue
            for part in path.relative_to(REPO).parts:
                self.assertIsNone(LEGACY.search(part), str(path.relative_to(REPO)))

    def test_plugins_start_with_prefix(self):
        for entry in listed_plugins():
            self.assertTrue(entry["name"].startswith(PREFIX), entry["name"])
            manifest = REPO / entry["source"] / ".claude-plugin" / "plugin.json"
            name = json.loads(manifest.read_text(encoding="utf-8"))["name"]
            self.assertTrue(name.startswith(PREFIX), f"{manifest}: {name}")

    def test_project_skills_start_with_prefix(self):
        for skill in sorted(p for p in (REPO / ".claude" / "skills").iterdir() if p.is_dir()):
            self.assertTrue(skill.name.startswith(PREFIX), skill.name)
            match = re.search(r"(?m)^name:\s*(\S+)", (skill / "SKILL.md").read_text(encoding="utf-8"))
            self.assertTrue(match and match.group(1).startswith(PREFIX), f"{skill.name}: frontmatter")


if __name__ == "__main__":
    unittest.main()
