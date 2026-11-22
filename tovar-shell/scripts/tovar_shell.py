#!/usr/bin/env python3
"""tovar-shell: writes your tmux config and menu, styled by a skin. Use the /tovar-shell:tmux skill."""
import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
MARKER = "# tovar-shell tmux config"
COLOR_KEYS = ("bg", "text", "dim", "accent", "accent2", "ink", "select_bg", "select_fg", "head")
LAYOUTS = ("buttons", "list")
BORDERS = ("single", "double", "rounded", "heavy")
PANE_LINES = ("single", "double", "heavy")
TMUX_ACTIONS = ("list", "status", "apply", "off", "show", "create")
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class ShellError(Exception):
    pass


# ---------- where things live ----------

def data_dir():
    raw = os.environ.get("CLAUDE_PLUGIN_DATA")
    if not raw:
        raise ShellError("CLAUDE_PLUGIN_DATA is not set. Run the command with --data <folder>.")
    return Path(raw)


def install_dir():
    return Path.home() / ".config" / "tmux" / "tovar"


def tmux_conf():
    return Path.home() / ".tmux.conf"


def example_skins():
    return PLUGIN / "tmux" / "skins"


def own_skins():
    return data_dir() / "skins"


def config_dir():
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


# ---------- small file helpers ----------

def read(path):
    path = Path(path)
    return path.read_text(encoding="utf-8") if path.is_file() else None


def write(path, text, mode=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    if mode is not None:
        tmp.chmod(mode)
    os.replace(tmp, path)


def read_json(path, what):
    text = read(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ShellError(f"{what} is not valid JSON, so nothing was changed.\n  {e}")


def state_path():
    return data_dir() / "state.json"


def load_state():
    data = read_json(state_path(), "state.json")
    return data if isinstance(data, dict) else {}


# ---------- skins ----------

def problems(skin):
    found = []
    colors = skin.get("colors") if isinstance(skin.get("colors"), dict) else {}
    menu = skin.get("menu") if isinstance(skin.get("menu"), dict) else {}
    tmux = skin.get("tmux") if isinstance(skin.get("tmux"), dict) else {}
    if not isinstance(skin.get("display"), str) or not skin["display"].strip():
        found.append("display is empty")
    for key in COLOR_KEYS + ("status_bg",):
        value = colors.get(key)
        if value is None and key == "status_bg":
            continue
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 255:
            found.append(f"colors.{key}: needs a 256-color number from 0 to 255")
    if menu.get("layout") not in LAYOUTS:
        found.append(f"menu.layout: one of {', '.join(LAYOUTS)}")
    for key in ("border", "border_selected"):
        if menu.get(key) not in BORDERS:
            found.append(f"menu.{key}: one of {', '.join(BORDERS)}")
    cursor = menu.get("cursor")
    if not isinstance(cursor, str) or not 1 <= len(cursor) <= 2:
        found.append("menu.cursor: 1 or 2 characters")
    rule = menu.get("rule")
    if not isinstance(rule, str) or len(rule) != 1:
        found.append("menu.rule: exactly 1 character")
    title = menu.get("title")
    if not isinstance(title, str) or not title.strip() or len(title) > 20:
        found.append("menu.title: text of at most 20 characters")
    if not isinstance(menu.get("title_format"), str) or "{}" not in menu["title_format"]:
        found.append("menu.title_format: text that contains {}")
    for key in ("spaced", "upper"):
        if not isinstance(menu.get(key), bool):
            found.append(f"menu.{key}: true or false")
    if tmux.get("pane_lines") not in PANE_LINES:
        found.append(f"tmux.pane_lines: one of {', '.join(PANE_LINES)}")
    return found


def skin_files():
    """name -> (kind, path). Your own skins hide an example with the same name."""
    found = {}
    for kind, folder in (("example", example_skins()), ("yours", own_skins() if os.environ.get("CLAUDE_PLUGIN_DATA") else None)):
        if folder and folder.is_dir():
            for path in sorted(folder.glob("*.json")):
                found[path.stem] = (kind, path)
    return found


def load_skin(name):
    files = skin_files()
    if name not in files:
        raise ShellError(f"No skin named '{name}'. Run: tovar_shell.py tmux list")
    skin = read_json(files[name][1], f"skin {name}")
    issues = problems(skin if isinstance(skin, dict) else {})
    if issues:
        raise ShellError(f"Skin '{name}' has problems:\n  " + "\n  ".join(issues))
    return skin


def legacy_theme():
    """Older tovar-themes-* plugins point settings.json at ~/.claude/tovar-themes/<name>/."""
    try:
        settings = read_json(config_dir() / "settings.json", "settings.json")
    except ShellError:
        return None
    tips = (settings or {}).get("spinnerTipsOverride") if isinstance(settings, dict) else None
    found = re.search(r"/tovar-themes/([a-z0-9-]+)/", str((tips or {}).get("tipsFile", "")))
    return found.group(1) if found else None


def active_theme():
    """The tovar theme that is active now, or None."""
    override = os.environ.get("TOVAR_STATE")
    paths = [Path(override)] if override else sorted((config_dir() / "plugins" / "data").glob("tovar-core*/state.json"))
    for path in paths:
        data = read_json(path, str(path))
        if isinstance(data, dict) and isinstance(data.get("theme"), str):
            return data["theme"]
    return legacy_theme()


def pick_skin(requested):
    """(skin name, why). A skin is picked by name, else by the active theme, else default."""
    files = skin_files()
    if requested:
        return requested, "chosen by you"
    theme = active_theme()
    if theme and theme in files:
        return theme, f"matches the active theme '{theme}'"
    if theme:
        return "default", f"the active theme '{theme}' has no skin yet"
    return "default", "no tovar theme is active"


# ---------- rendering ----------

def fill(text, values):
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def render(name):
    """Every file a skin needs: path -> (text, mode)."""
    skin = load_skin(name)
    colors, menu, tmux = skin["colors"], skin["menu"], skin["tmux"]
    folder = install_dir()
    values = {**colors, "status_bg": colors.get("status_bg", colors["bg"]),
              "skin": name, "dir": folder, "pane_lines": tmux["pane_lines"],
              "popup_border": menu["border"]}
    src = PLUGIN / "tmux"
    return {
        tmux_conf(): (fill(read(src / "tmux.conf.tmpl"), values), None),
        folder / "open.sh": (fill(read(src / "open.sh.tmpl"), values), 0o755),
        folder / "menu.py": (read(src / "menu.py"), 0o755),
        folder / "skin.json": (json.dumps(skin, ensure_ascii=False, indent=2) + "\n", None),
    }


def is_managed(text):
    return text is not None and text.startswith(MARKER)


def new_backup():
    root = data_dir() / "backups"
    stamp = time.strftime("%Y%m%d-%H%M%S")
    folder, n = root / stamp, 1
    while folder.exists():
        n += 1
        folder = root / f"{stamp}-{n}"
    folder.mkdir(parents=True)
    return folder


def short_diff(path, before, after, limit=40):
    diff = list(difflib.unified_diff((before or "").splitlines(), (after or "").splitlines(),
                                     fromfile=f"{path} (now)", tofile=f"{path} (after)", lineterm=""))
    return diff[:limit] + ([f"... {len(diff) - limit} more lines"] if len(diff) > limit else [])


def reload_tmux():
    try:
        done = subprocess.run(["tmux", "source-file", str(tmux_conf())], capture_output=True, text=True)
    except OSError:
        return "tmux is not installed, nothing to reload."
    return "Reloaded tmux." if done.returncode == 0 else "No running tmux to reload. It loads on the next start."


# ---------- actions ----------

def do_list(args):
    files = skin_files()
    theme, state = active_theme(), load_state().get("tmux") or {}
    rows = []
    for name, (kind, path) in sorted(files.items()):
        skin = read_json(path, name) or {}
        marks = ("*" if name == state.get("skin") else " ") + ("~" if name == theme else " ")
        rows.append({"name": name, "kind": kind, "display": skin.get("display", name),
                     "applied": name == state.get("skin"), "matches_theme": name == theme})
        if not args.json:
            print(f"{marks} {name} ({kind}): {skin.get('display', name)}")
    if args.json:
        print(json.dumps({"active_theme": theme, "skins": rows}, ensure_ascii=False, indent=2))
    else:
        print("* applied now, ~ matches the active tovar theme")
    return 0


def do_status(args):
    state = load_state().get("tmux") or {}
    conf = read(tmux_conf())
    theme = active_theme()
    skin, why = pick_skin(None)
    info = {"applied_skin": state.get("skin"), "managed": is_managed(conf), "active_theme": theme,
            "suggested_skin": skin, "suggested_because": why, "install_dir": str(install_dir())}
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return 0
    print(f"applied skin: {info['applied_skin'] or 'none'}")
    print(f"tmux config managed by tovar-shell: {'yes' if info['managed'] else 'no'}")
    print(f"active tovar theme: {theme or 'none'}")
    print(f"suggested skin: {skin} ({why})")
    return 0


def do_apply(args):
    name, why = pick_skin(args.name)
    out = render(name)
    old = read(tmux_conf())
    backup = old is not None and not is_managed(old)
    lines = [f"Skin: {name} ({why})."]
    for path, (text, _) in out.items():
        if read(path) != text:
            lines.append(f"{'Would write' if args.dry_run else 'Wrote'} {path}")
    if backup:
        lines.append(f"Your current {tmux_conf()} is saved first, so 'off' can put it back.")
    if args.dry_run:
        lines += short_diff(tmux_conf(), old, out[tmux_conf()][0])
        print("\n".join(lines))
        return 0
    state = load_state()
    prior = (state.get("tmux") or {}).get("backup")
    if backup:
        folder = new_backup()
        write(folder / "tmux.conf", old)
        prior = folder.name
    for path, (text, mode) in out.items():
        write(path, text, mode)
    state["tmux"] = {"skin": name, "backup": prior}
    write(state_path(), json.dumps(state, indent=2) + "\n")
    if args.reload:
        lines.append(reload_tmux())
    print("\n".join(lines))
    return 0


def do_off(args):
    state = load_state()
    info = state.get("tmux") or {}
    conf = read(tmux_conf())
    if not is_managed(conf):
        print("Your tmux config is not managed by tovar-shell, so nothing was changed.")
        return 0
    backup = info.get("backup")
    original = read(data_dir() / "backups" / backup / "tmux.conf") if backup else None
    action = "restore your previous ~/.tmux.conf" if original is not None else "remove ~/.tmux.conf"
    if args.dry_run:
        print(f"Would {action} and delete {install_dir()}.")
        return 0
    if original is not None:
        write(tmux_conf(), original)
    else:
        tmux_conf().unlink(missing_ok=True)
    shutil.rmtree(install_dir(), ignore_errors=True)
    state.pop("tmux", None)
    write(state_path(), json.dumps(state, indent=2) + "\n")
    print(f"Done: {action} and deleted {install_dir()}. Restart tmux (or run: tmux kill-server) to drop the old look.")
    return 0


def do_show(args):
    if not args.name:
        raise ShellError("Say which skin: tovar_shell.py tmux show <name>")
    print(json.dumps(load_skin(args.name), ensure_ascii=False, indent=2))
    return 0


def do_create(args):
    if not args.name or not NAME.match(args.name):
        raise ShellError("Give the skin a name: lowercase letters, digits and hyphens, for example star-wars.")
    if not args.file:
        raise ShellError("Pass the skin draft with --file <draft.json>. Copy one with: tovar_shell.py tmux show <skin>")
    skin = read_json(args.file, args.file)
    issues = problems(skin if isinstance(skin, dict) else {})
    if issues:
        print("The skin has problems:\n  " + "\n  ".join(issues), file=sys.stderr)
        return 1
    target = own_skins() / f"{args.name}.json"
    if args.dry_run:
        print(f"Would write {target}")
        return 0
    write(target, json.dumps(skin, ensure_ascii=False, indent=2) + "\n")
    print(f"Saved skin '{args.name}' to {target}. Apply it with: tovar_shell.py tmux apply {args.name}")
    return 0


ACTIONS = {"list": do_list, "status": do_status, "apply": do_apply, "off": do_off,
           "show": do_show, "create": do_create}


def build_parser():
    p = argparse.ArgumentParser(prog="tovar_shell.py", description="tovar-shell: shell tools styled by tovar themes.")
    p.add_argument("area", choices=["tmux"])
    p.add_argument("action", choices=TMUX_ACTIONS)
    p.add_argument("name", nargs="?", help="a skin name")
    p.add_argument("--file", help="skin draft for create")
    p.add_argument("--dry-run", action="store_true", help="show the change, write nothing")
    p.add_argument("--reload", action="store_true", help="reload a running tmux after the change")
    p.add_argument("--json", action="store_true", help="print machine readable output")
    p.add_argument("--data", help="the tovar-shell data folder (default: $CLAUDE_PLUGIN_DATA)")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.data:
        os.environ["CLAUDE_PLUGIN_DATA"] = args.data
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    try:
        return ACTIONS[args.action](args)
    except (ShellError, OSError) as e:
        print(f"tovar-shell: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
