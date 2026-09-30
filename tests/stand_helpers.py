"""Shared setup for the Stand tests: temp data, config and examples folders."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "stand" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def ns(action=None, *names, **options):
    """Build the arguments the CLI would hand to an area's run()."""
    values = dict(area=None, action=action, names=list(names), file=None, from_=None,
                  to=None, dry_run=False, json=False, data=None)
    values.update(options)
    return argparse.Namespace(**values)


def sample_theme(display="Star Wars", **override):
    """A valid theme draft: 15 facts (the engine adds the 5 plugin tips)."""
    theme = {
        "display": display,
        "tipsLabel": "Holocron",
        "verbs": [f"Verb {i}" for i in range(40)],
        "announcements": [f"Line {i}" for i in range(20)],
        "tips": [f"Fact {i}" for i in range(15)],
        "names": [f"Name {i}" for i in range(100)],
    }
    theme.update(override)
    return theme


class StandCase(unittest.TestCase):
    """Runs every test against fresh temp folders. Never touches real files."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        self.data = self.tmp / "data"
        self.config = self.tmp / "config"
        self.examples = self.tmp / "examples"
        for folder in (self.data, self.config, self.examples):
            folder.mkdir()
        patch = mock.patch.dict(os.environ, {
            "CLAUDE_PLUGIN_DATA": str(self.data),
            "CLAUDE_CONFIG_DIR": str(self.config),
            "STAND_EXAMPLES": str(self.examples),
        })
        patch.start()
        self.addCleanup(patch.stop)

    def draft(self, theme=None, name="draft.json"):
        path = self.tmp / name
        path.write_text(json.dumps(theme or sample_theme(), ensure_ascii=False), encoding="utf-8")
        return path

    def read_json(self, path):
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def settings(self):
        return self.read_json(self.config / "settings.json")

    def run_cli(self, *args, stdin=""):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "stand.py"), *args],
            input=stdin, capture_output=True, text=True, encoding="utf-8",
        )
