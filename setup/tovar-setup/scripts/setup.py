#!/usr/bin/env python3
"""Engine for the tovar-setup plugin.

  plan-settings         print, as JSON, what apply-settings would change
  apply-settings        write the approved settings into settings.json
"""
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
SETUP_JSON = PLUGIN / "setup.json"
SETTINGS_KEYS = ("model", "effortLevel", "outputStyle", "tui", "autoUpdatesChannel")
EMPTY_SETUP = {
    "marketplaces": [], "plugins": [], "settings": {}, "statusline": None,
    "claude_md": {"text": ""},
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def config_dir():
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def state_dir():
    d = config_dir() / "tovar-setup"
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_setup():
    if not SETUP_JSON.is_file():
        return dict(EMPTY_SETUP)
    merged = dict(EMPTY_SETUP)
    merged.update(load_json(SETUP_JSON))
    return merged


def read_settings():
    path = config_dir() / "settings.json"
    if not path.is_file():
        return path, {}
    try:
        return path, load_json(path)
    except json.JSONDecodeError as e:
        sys.exit(f"Your settings file is not valid JSON, so nothing was changed.\n  {path}: {e}")


def backup_file(path):
    if not path.is_file():
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = state_dir() / f"{path.name}.backup.{stamp}"
    n = 1
    while dest.exists():
        n += 1
        dest = state_dir() / f"{path.name}.backup.{stamp}-{n}"
    dest.write_bytes(path.read_bytes())
    print(f"Backed up {path.name} to:\n  {dest}")


def write_json_atomic(path, data):
    target = path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        if target.exists():
            shutil.copymode(target, tmp)
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def local_settings_subset(s):
    return {k: s[k] for k in SETTINGS_KEYS if k in s}


def plan_settings(setup, s):
    wanted = setup["settings"]
    if not wanted:
        return {"status": "empty"}
    changes = {k: v for k, v in wanted.items() if s.get(k) != v}
    return {"status": "differs" if changes else "match", "changes": changes}


def cmd_plan_settings(args):
    setup = read_setup()
    _, s = read_settings()
    print(json.dumps(plan_settings(setup, s), ensure_ascii=False))


def cmd_apply_settings(args):
    setup = read_setup()
    path, s = read_settings()
    plan = plan_settings(setup, s)
    if plan["status"] == "empty":
        print("settings: nothing captured, so nothing to do")
        return
    if not plan["changes"]:
        print("settings: already matches, nothing to do")
        return
    backup_file(path)
    s.update(plan["changes"])
    write_json_atomic(path, s)
    for k, v in plan["changes"].items():
        print(f"settings: set {k} = {v!r}")


COMMANDS = {
    "plan-settings": cmd_plan_settings,
    "apply-settings": cmd_apply_settings,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](sys.argv[2:])
