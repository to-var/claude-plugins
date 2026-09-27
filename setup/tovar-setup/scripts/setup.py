#!/usr/bin/env python3
"""Engine for the tovar-setup plugin.

  plan-settings         print, as JSON, what apply-settings would change
  apply-settings        write the approved settings into settings.json
  plan-statusline       print, as JSON, what apply-statusline would change
  apply-statusline      write the approved status line into settings.json
  read-md               print ~/.claude/CLAUDE.md split into sections as JSON
  save-md               read {"text": "..."} JSON on stdin into setup.json
  plan-claude-md        print, as JSON, whether the CLAUDE.md block matches
  apply-claude-md       write the approved block into CLAUDE.md
  plan-plugins          print, as JSON, which marketplaces/plugins are missing
  apply-plugins         install the approved marketplaces and plugins
  read-state            print this machine's marketplaces, plugins, settings
                         and statusLine as JSON, for capture to ask about
  save-state            read approved JSON on stdin into setup.json
"""
import json
import os
import shutil
import subprocess
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


def plan_statusline(setup, s):
    wanted = setup["statusline"]
    if not wanted:
        return {"status": "empty"}
    return {"status": "match" if s.get("statusLine") == wanted else "differs", "value": wanted}


def cmd_plan_statusline(args):
    setup = read_setup()
    _, s = read_settings()
    print(json.dumps(plan_statusline(setup, s), ensure_ascii=False))


def cmd_apply_statusline(args):
    setup = read_setup()
    path, s = read_settings()
    plan = plan_statusline(setup, s)
    if plan["status"] == "empty":
        print("statusline: nothing captured, so nothing to do")
        return
    if plan["status"] == "match":
        print("statusline: already matches, nothing to do")
        return
    backup_file(path)
    s["statusLine"] = setup["statusline"]
    write_json_atomic(path, s)
    print("statusline: updated")


MD_BEGIN = "<!-- tovar-setup:begin -->"
MD_END = "<!-- tovar-setup:end -->"


def claude_md_path():
    return config_dir() / "CLAUDE.md"


def write_text_atomic(path, text):
    target = path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        if target.exists():
            shutil.copymode(target, tmp)
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def split_sections(text):
    sections = []
    heading, body = None, []
    for line in text.splitlines():
        if line.startswith("## "):
            sections.append({"heading": heading, "text": "\n".join(body).strip()})
            heading, body = line[3:].strip(), []
        else:
            body.append(line)
    sections.append({"heading": heading, "text": "\n".join(body).strip()})
    return [s for s in sections if s["heading"] or s["text"]]


def cmd_read_md(args):
    path = claude_md_path()
    if not path.is_file():
        print(json.dumps({"exists": False, "sections": []}))
        return
    sections = split_sections(path.read_text(encoding="utf-8"))
    print(json.dumps({"exists": True, "sections": sections}, ensure_ascii=False))


def cmd_save_md(args):
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        sys.exit(f'save-md needs {{"text": "..."}} as valid JSON on stdin: {e}')
    if not isinstance(data, dict) or "text" not in data or not isinstance(data["text"], str):
        sys.exit('save-md needs {"text": "..."} on stdin')
    text = data["text"]
    setup = read_setup()
    setup["claude_md"] = {"text": text.strip()}
    write_json_atomic(SETUP_JSON, setup)
    if text.strip():
        print("Saved the approved CLAUDE.md text to setup.json.")
    else:
        print("Cleared the CLAUDE.md text in setup.json.")


def md_block(text):
    return f"{MD_BEGIN}\n{text}\n{MD_END}"


def plan_claude_md(setup):
    text = setup["claude_md"]["text"]
    if not text:
        return {"status": "empty"}
    path = claude_md_path()
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    return {"status": "match" if md_block(text) in current else "differs"}


def cmd_plan_claude_md(args):
    print(json.dumps(plan_claude_md(read_setup()), ensure_ascii=False))


def _has_clean_block(current):
    """Check if current has exactly one balanced MD_BEGIN/MD_END pair."""
    return (current.count(MD_BEGIN) == 1 and current.count(MD_END) == 1
            and current.index(MD_BEGIN) < current.index(MD_END))


def cmd_apply_claude_md(args):
    setup = read_setup()
    plan = plan_claude_md(setup)
    if plan["status"] == "empty":
        print("claude_md: nothing captured, so nothing to do")
        return
    if plan["status"] == "match":
        print("claude_md: already matches, nothing to do")
        return
    path = claude_md_path()
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    block = md_block(setup["claude_md"]["text"])
    if _has_clean_block(current):
        pre = current.split(MD_BEGIN)[0]
        post = current.split(MD_END)[1]
        new = pre + block + post
    elif current.strip():
        new = current.rstrip("\n") + "\n\n" + block + "\n"
    else:
        new = block + "\n"
    if path.is_file():
        backup_file(path)
    write_text_atomic(path, new)
    print("claude_md: updated")


def claude_cmd():
    raw = os.environ.get("TOVAR_SETUP_CLAUDE_CMD_JSON")
    return json.loads(raw) if raw else ["claude"]


def local_plugin_state(s):
    known = s.get("extraKnownMarketplaces") or {}
    enabled = {k for k, v in (s.get("enabledPlugins") or {}).items() if v}
    return known, enabled


def plan_plugins(setup, s):
    if not setup["marketplaces"] and not setup["plugins"]:
        return {"status": "empty"}
    known, enabled = local_plugin_state(s)
    add_market = [m for m in setup["marketplaces"] if m["name"] not in known]
    add_plugin = [p for p in setup["plugins"] if p not in enabled]
    status = "match" if not add_market and not add_plugin else "differs"
    return {"status": status, "marketplaces": add_market, "plugins": add_plugin}


def cmd_plan_plugins(args):
    setup = read_setup()
    _, s = read_settings()
    print(json.dumps(plan_plugins(setup, s), ensure_ascii=False))


def cmd_apply_plugins(args):
    setup = read_setup()
    _, s = read_settings()
    plan = plan_plugins(setup, s)
    if plan["status"] == "empty":
        print("plugins: nothing captured, so nothing to do")
        return
    if plan["status"] == "match":
        print("plugins: already matches, nothing to do")
        return
    if claude_cmd() == ["claude"] and not shutil.which("claude"):
        print("plugins: claude is not on PATH, so nothing was installed")
        return
    for m in plan["marketplaces"]:
        r = subprocess.run(claude_cmd() + ["plugin", "marketplace", "add", m["repo"]],
                            capture_output=True, text=True)
        if r.returncode == 0:
            print(f"plugins: added marketplace {m['name']}")
        else:
            print(f"plugins: error adding marketplace {m['name']}: {(r.stdout + r.stderr).strip()}")
    for p in plan["plugins"]:
        r = subprocess.run(claude_cmd() + ["plugin", "install", p],
                            capture_output=True, text=True)
        if r.returncode == 0:
            print(f"plugins: installed {p}")
        else:
            print(f"plugins: error installing {p}: {(r.stdout + r.stderr).strip()}")


def cmd_read_state(args):
    _, s = read_settings()
    known, enabled = local_plugin_state(s)
    print(json.dumps({
        "marketplaces": known,
        "plugins": sorted(enabled),
        "settings": local_settings_subset(s),
        "statusline": s.get("statusLine"),
    }, ensure_ascii=False))


def cmd_save_state(args):
    approved = json.load(sys.stdin)
    setup = read_setup()
    for key in ("marketplaces", "plugins", "statusline"):
        if key in approved:
            setup[key] = approved[key]
    if "settings" in approved:
        setup["settings"] = {k: v for k, v in approved["settings"].items() if k in SETTINGS_KEYS}
    write_json_atomic(SETUP_JSON, setup)
    print("Saved the approved setup to setup.json.")


COMMANDS = {
    "plan-settings": cmd_plan_settings,
    "apply-settings": cmd_apply_settings,
    "plan-statusline": cmd_plan_statusline,
    "apply-statusline": cmd_apply_statusline,
    "read-md": cmd_read_md,
    "save-md": cmd_save_md,
    "plan-claude-md": cmd_plan_claude_md,
    "apply-claude-md": cmd_apply_claude_md,
    "plan-plugins": cmd_plan_plugins,
    "apply-plugins": cmd_apply_plugins,
    "read-state": cmd_read_state,
    "save-state": cmd_save_state,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](sys.argv[2:])
