"""Shared test setup: a throwaway copy of the marketplace folder."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


EMPTY_SETUP = {
    "marketplaces": [], "plugins": [], "settings": {}, "statusline": None,
    "claude_md": {"text": ""},
}


def make_setup_root(tmp):
    # Copy the plugin, then reset setup.json to the empty scaffold: the real
    # repo's setup.json holds Jose's actual captured data, and tests need a
    # pristine "nothing captured yet" starting point regardless of that.
    root = Path(tmp) / "setuproot"
    shutil.copytree(REPO / "setup" / "tovar-setup", root)
    (root / "setup.json").write_text(json.dumps(EMPTY_SETUP), encoding="utf-8")
    return root


def run_setup(plugin, cmd, *, stdin="", env=None, cfg=None):
    full_env = {**os.environ, **(env or {})}
    if cfg is not None:
        full_env["CLAUDE_CONFIG_DIR"] = str(cfg)
    return subprocess.run(
        [sys.executable, str(plugin / "scripts" / "setup.py"), cmd],
        input=stdin, capture_output=True, text=True, env=full_env,
    )


def make_fake_claude(tmp):
    script = Path(tmp) / "fake_claude.py"
    script.write_text(
        "import json, os, sys\n"
        "log = os.environ['FAKE_CLAUDE_LOG']\n"
        "with open(log, 'a', encoding='utf-8') as f:\n"
        "    f.write(json.dumps(sys.argv[1:]) + chr(10))\n"
        "fail = os.environ.get('FAKE_CLAUDE_FAIL', '')\n"
        "sys.exit(1 if fail and fail in sys.argv else 0)\n",
        encoding="utf-8",
    )
    return script
