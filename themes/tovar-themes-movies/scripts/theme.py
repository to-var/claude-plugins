#!/usr/bin/env python3
"""Theme engine shared by every tovar-themes plugin.

  on    write this theme into the user settings and turn the other themes off
  off   remove this theme's values from the user settings, if it owns them
  name  PreToolUse hook: give a subagent a random name from this theme
"""
import json
import os
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path

PREFIX = "tovar-themes-"
PLUGIN = Path(__file__).resolve().parent.parent
THEME_KEYS = ("spinnerVerbs", "companyAnnouncements", "spinnerTipsOverride")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def plugin_name():
    return load_json(PLUGIN / ".claude-plugin" / "plugin.json")["name"]


def config_dir():
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def themes_state():
    return config_dir() / "tovar-themes"


def state_dir(name):
    return themes_state() / name[len(PREFIX):]


def read_settings():
    path = config_dir() / "settings.json"
    if not path.is_file():
        sys.exit(f"No settings file at {path}")
    try:
        return path, load_json(path)
    except json.JSONDecodeError as e:
        sys.exit(f"Your settings file is not valid JSON, so nothing was changed.\n  {path}: {e}")


def backup(path, state):
    state.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = state / f"settings.backup.{stamp}.json"
    n = 1
    while dest.exists():
        n += 1
        dest = state / f"settings.backup.{stamp}-{n}.json"
    dest.write_bytes(path.read_bytes())
    print(f"Backed up your settings to:\n  {dest}")


def write_settings(path, settings):
    # Write a temp file beside the real one, then swap it in, so a crash never
    # leaves a half-written settings file. Resolve first to keep a symlink intact.
    target = path.resolve()
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(settings, ensure_ascii=False, indent=2) + "\n")
        shutil.copymode(target, tmp)
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def active_theme(settings):
    tips = settings.get("spinnerTipsOverride") or {}
    tips_file = tips.get("tipsFile")
    if not tips_file:
        return "no theme is active"
    p = Path(tips_file)
    if p.parent.parent == themes_state():
        return f"the active theme is {PREFIX}{p.parent.name}"
    return f"the active tips label is {tips.get('label', 'unnamed')}"


def cmd_on():
    theme = load_json(PLUGIN / "theme.json")
    name = plugin_name()
    path, s = read_settings()
    state = state_dir(name)
    backup(path, state)

    turned_off = []
    enabled = s.get("enabledPlugins") or {}
    for key, on in enabled.items():
        other = key.split("@", 1)[0]
        if other == name:
            # Keep this theme enabled, even if another theme's "on" just turned it off.
            enabled[key] = True
        elif on is True and other.startswith(PREFIX):
            enabled[key] = False
            turned_off.append(key)

    tips_file = state / "tips.json"
    tips_file.write_text(
        json.dumps(theme["tips"], ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    s["spinnerVerbs"] = {"mode": "replace", "verbs": theme["verbs"]}
    s["companyAnnouncements"] = theme["announcements"]
    s["spinnerTipsOverride"] = {"tipsFile": str(tips_file), "label": theme["tipsLabel"]}
    write_settings(path, s)

    for key in turned_off:
        print(f"Turned off {key}")
    print(f"Wrote the {theme['display']} theme: {len(theme['verbs'])} spinner verbs, "
          f"{len(theme['announcements'])} startup lines and {len(theme['tips'])} tips. "
          "Your status line was not touched.")
    print("Restart Claude Code to see it.")


def cmd_off():
    theme = load_json(PLUGIN / "theme.json")
    name = plugin_name()
    path, s = read_settings()
    mine = str(state_dir(name) / "tips.json")
    if (s.get("spinnerTipsOverride") or {}).get("tipsFile") != mine:
        print(f"The {theme['display']} theme is not active ({active_theme(s)}). Nothing changed.")
        return

    backup(path, state_dir(name))
    for key in THEME_KEYS:
        s.pop(key, None)
    write_settings(path, s)
    print(f"Removed the {theme['display']} spinner verbs, startup lines and tips.")


def cmd_name():
    # Never block a subagent: on any problem, print nothing and let it start unchanged.
    try:
        event = json.loads(sys.stdin.read())
        names = load_json(PLUGIN / "theme.json").get("names") or []
    except (OSError, ValueError):
        return
    if not names or not isinstance(event, dict):
        return
    tool_input = event.get("tool_input")
    tool_input = dict(tool_input) if isinstance(tool_input, dict) else {}
    tool_input["description"] = random.choice(names)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": tool_input,
            "updatedToolInput": tool_input,
        }
    }, ensure_ascii=False))


COMMANDS = {"on": cmd_on, "off": cmd_off, "name": cmd_name}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        sys.exit("usage: theme.py on|off|name")
    COMMANDS[sys.argv[1]]()
