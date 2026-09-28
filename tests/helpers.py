"""Shared test setup: a throwaway copy of the marketplace folder."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def make_root(tmp):
    root = Path(tmp) / "root"
    shutil.copytree(REPO / "template", root / "template")
    shutil.copytree(REPO / "tools", root / "tools")
    (root / "themes").mkdir()
    (root / ".claude-plugin").mkdir()
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"name": "test-market", "owner": {"name": "Test"}, "plugins": []}),
        encoding="utf-8",
    )
    return root


def run_tools(root, *args, env=None):
    return subprocess.run(
        [sys.executable, str(root / "tools" / "themes.py"), *args],
        capture_output=True, text=True, env=env,
    )


def content(display, label, names):
    return {
        "display": display,
        "tipsLabel": label,
        "verbs": [f"{display} verb {i}" for i in range(40)],
        "announcements": [f"{display} line {i}" for i in range(20)],
        "tips": [f"{display} tip {i}" for i in range(20)],
        "names": names,
    }


def make_theme(root, theme, display, label, names):
    result = run_tools(root, "new", theme, display)
    assert result.returncode == 0, result.stderr
    plugin = root / "themes" / f"tovar-themes-{theme}"
    (plugin / "theme.json").write_text(
        json.dumps(content(display, label, names), ensure_ascii=False), encoding="utf-8"
    )
    return plugin


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
