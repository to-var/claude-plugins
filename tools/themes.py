#!/usr/bin/env python3
"""Builder for the tovar-themes plugin family.

  new <theme> [display name]   make a theme plugin from the template
  sync                         copy the template into every theme
  check [theme ...]            check theme content and run the plugin checker
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PREFIX = "tovar-themes-"
ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "template"
THEMES = ROOT / "themes"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SKIP = {".DS_Store", "__pycache__"}
COUNTS = {"verbs": 40, "announcements": 20, "tips": 20}
MIN_NAMES = 100


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def description(display):
    return f"{display} theme for Claude Code: spinner verbs, startup lines, tips and subagent names."


def render(dest, theme, display):
    for src in sorted(TEMPLATE.rglob("*")):
        rel = src.relative_to(TEMPLATE)
        if src.is_dir() or SKIP & set(rel.parts):
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8")
        # DISPLAY_JSON is the name escaped for a double-quoted JSON or YAML string.
        display_json = json.dumps(display, ensure_ascii=False)[1:-1]
        text = text.replace("{{THEME}}", theme).replace("{{DISPLAY_JSON}}", display_json)
        out.write_text(text.replace("{{DISPLAY}}", display), encoding="utf-8")
        shutil.copymode(src, out)


def theme_dirs():
    if not THEMES.is_dir():
        return []
    return sorted(p for p in THEMES.iterdir() if p.is_dir() and p.name.startswith(PREFIX))


def blank_content(theme, display):
    return {
        "_todo": "Fill in tipsLabel, 40 verbs, 20 announcements, 15 more tips (keep these 5) "
                 "and at least 100 names, then delete this line.",
        "display": display,
        "tipsLabel": "",
        "verbs": [],
        "announcements": [],
        "tips": [
            f"Subagents get {display} names. Check the task list.",
            f"Run /{PREFIX}{theme}:off to put these settings back the way they were.",
            "Every theme setting lives in its plugin folder, not scattered in settings.json.",
            f"/{PREFIX}{theme}:on backs up your settings before it changes anything.",
            "Turning on another theme turns this one off.",
        ],
        "names": [],
    }


def cmd_new(args):
    if not 1 <= len(args) <= 2:
        sys.exit("usage: themes.py new <theme> [display name]")
    theme = args[0]
    if not NAME.match(theme):
        sys.exit(f"'{theme}' is not a valid theme name. Use lowercase letters, digits and hyphens.")
    plugin = PREFIX + theme
    dest = THEMES / plugin
    if dest.exists():
        sys.exit(f"{plugin} already exists.")
    display = args[1] if len(args) == 2 else theme.replace("-", " ").title()

    render(dest, theme, display)
    write_json(dest / "theme.json", blank_content(theme, display))

    market = read_json(MARKETPLACE)
    market.setdefault("plugins", []).append(
        {"name": plugin, "source": f"./themes/{plugin}", "description": description(display)}
    )
    write_json(MARKETPLACE, market)

    print(f"Created {plugin}.")
    print(f"Fill in its theme.json, then run: python3 tools/themes.py check {theme}")


def cmd_sync(args):
    if args:
        sys.exit("usage: themes.py sync")
    dirs = theme_dirs()
    for d in dirs:
        render(d, d.name[len(PREFIX):], read_json(d / "theme.json")["display"])
        print(f"Synced {d.name}")
    if not dirs:
        print("No themes found.")


def problems(d):
    try:
        c = read_json(d / "theme.json")
    except (OSError, json.JSONDecodeError) as e:
        return [f"theme.json: {e}"]
    found = []
    if "_todo" in c:
        found.append("the _todo line is still there")
    for key in ("display", "tipsLabel"):
        if not isinstance(c.get(key), str) or not c[key].strip():
            found.append(f"{key} is empty")
    lists = {key: c.get(key) if isinstance(c.get(key), list) else [] for key in [*COUNTS, "names"]}
    for key, n in COUNTS.items():
        if len(lists[key]) != n:
            found.append(f"{key}: needs {n}, has {len(lists[key])}")
    if len(lists["names"]) < MIN_NAMES:
        found.append(f"names: needs at least {MIN_NAMES}, has {len(lists['names'])}")
    for key, items in lists.items():
        text = [i for i in items if isinstance(i, str) and i.strip()]
        if len(text) != len(items):
            found.append(f"{key}: every item must be non-empty text")
        repeated = sorted({i for i in text if text.count(i) > 1})
        if repeated:
            found.append(f"{key}: repeated: {', '.join(repeated)}")
    return found + validate(d)


def validate(d):
    if os.environ.get("TOVAR_THEMES_SKIP_VALIDATE"):
        return []
    if not shutil.which("claude"):
        return ["claude is not on PATH, so the plugin checker did not run"]
    r = subprocess.run(["claude", "plugin", "validate", str(d)], capture_output=True, text=True)
    output = (r.stdout + r.stderr).strip()
    if r.returncode != 0 or "⚠" in output:
        return [f"plugin checker:\n{output}"]
    return []


def cmd_check(args):
    dirs = [THEMES / (PREFIX + a) for a in args] if args else theme_dirs()
    if not dirs:
        sys.exit("No themes found.")
    failed = False
    for d in dirs:
        if not d.is_dir():
            print(f"{d.name}: not found")
            failed = True
            continue
        found = problems(d)
        if found:
            print(f"{d.name}:")
            for p in found:
                print(f"  - {p}")
            failed = True
        else:
            print(f"{d.name}: OK")
    sys.exit(1 if failed else 0)


COMMANDS = {"new": cmd_new, "sync": cmd_sync, "check": cmd_check}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](sys.argv[2:])
