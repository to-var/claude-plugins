"""Theme area: content rules, saving, reading and exporting themes."""
import json
import random
import re
from pathlib import Path

from . import StandError, claude_settings, files, items, paths, state
from .files import Change, dump_json
from .result import Result

THEMES = items.Area("themes", folder=True)
KEYS = ("display", "tipsLabel", "verbs", "announcements", "tips", "names")
TEXT_KEYS = ("display", "tipsLabel")
COUNTS = {"verbs": 40, "announcements": 20, "tips": 20}
MIN_NAMES = 100
MAX_LEN = {"verbs": 30, "announcements": 90, "tips": 90, "names": 20}

# The five tips that explain the plugin. Old copies from the tovar-themes plugins match too.
PLUGIN_TIP = re.compile(
    r"^(Subagents get .* names\. Check the task list\."
    r"|Run /stand:undo to put your settings back the way they were\."
    r"|Stand keeps every theme in its own data folder, not scattered in settings\.json\."
    r"|Applying a Stand theme backs up your settings before it changes anything\."
    r"|Only one Stand theme is active at a time\."
    r"|Run /tovar-themes-[a-z0-9-]+:off to put these settings back the way they were\."
    r"|Every theme setting lives in its plugin folder, not scattered in settings\.json\."
    r"|/tovar-themes-[a-z0-9-]+:on backs up your settings before it changes anything\."
    r"|Turning on another theme turns this one off\.)$"
)


def plugin_tips(display):
    return [
        f"Subagents get {display} names. Check the task list.",
        "Run /stand:undo to put your settings back the way they were.",
        "Stand keeps every theme in its own data folder, not scattered in settings.json.",
        "Applying a Stand theme backs up your settings before it changes anything.",
        "Only one Stand theme is active at a time.",
    ]


def normalize(theme):
    """Keep only the known keys. The 5 plugin tips always come first, fresh for this display name."""
    clean = {k: theme.get(k, "" if k in TEXT_KEYS else []) for k in KEYS}
    tips = clean["tips"] if isinstance(clean["tips"], list) else []
    facts = [t for t in tips if not (isinstance(t, str) and PLUGIN_TIP.match(t))]
    display = clean["display"] if isinstance(clean["display"], str) else ""
    clean["tips"] = plugin_tips(display) + facts
    return clean


def problems(theme):
    found = []
    for key in TEXT_KEYS:
        if not isinstance(theme.get(key), str) or not theme[key].strip():
            found.append(f"{key} is empty")
    for key in ("verbs", "announcements", "tips", "names"):
        value = theme.get(key)
        entries = value if isinstance(value, list) else []
        if key in COUNTS and len(entries) != COUNTS[key]:
            found.append(f"{key}: needs {COUNTS[key]}, has {len(entries)}")
        if key == "names" and len(entries) < MIN_NAMES:
            found.append(f"names: needs at least {MIN_NAMES}, has {len(entries)}")
        text = [e for e in entries if isinstance(e, str) and e.strip()]
        if len(text) != len(entries):
            found.append(f"{key}: every item must be non-empty text")
        too_long = [e for e in text if len(e) > MAX_LEN[key]]
        if too_long:
            found.append(f"{key}: longer than {MAX_LEN[key]} characters: {', '.join(too_long[:3])}")
        repeated = sorted({e for e in text if text.count(e) > 1})
        if repeated:
            found.append(f"{key}: repeated: {', '.join(repeated)}")
    return found


def as_dict(value):
    return value if isinstance(value, dict) else {}


def item_files(theme):
    """The three files that make up a saved theme."""
    return {
        "settings.json": dump_json({
            "spinnerVerbs": {"mode": "replace", "verbs": theme["verbs"]},
            "companyAnnouncements": theme["announcements"],
            "spinnerTipsOverride": {"tipsFile": "tips.json", "label": theme["tipsLabel"]},
        }),
        "tips.json": dump_json(theme["tips"]),
        "extras.json": dump_json({"display": theme["display"], "names": theme["names"]}),
    }


def item_changes(folder, theme, backup):
    return [Change(Path(folder) / name, text, backup=backup) for name, text in item_files(theme).items()]


def theme_from_settings(path):
    """Read a Claude settings file (or a saved theme's settings.json) as a theme."""
    path = Path(path)
    settings = files.read_json_file(path)
    if not isinstance(settings, dict):
        raise StandError(f"{path}: not a settings file.")
    override = as_dict(settings.get("spinnerTipsOverride"))
    tips = override.get("tips", [])
    if override.get("tipsFile"):
        tips_path = Path(override["tipsFile"])
        if not tips_path.is_absolute():
            tips_path = path.parent / tips_path
        loaded = files.read_json_file(tips_path)
        if isinstance(loaded, list):
            tips = loaded
    extras = as_dict(files.read_json_file(path.parent / "extras.json"))
    return {
        "display": extras.get("display", ""),
        "tipsLabel": override.get("label", ""),
        "verbs": as_dict(settings.get("spinnerVerbs")).get("verbs", []),
        "announcements": settings.get("companyAnnouncements", []),
        "tips": tips,
        "names": extras.get("names", []),
    }


def read_theme(folder):
    return theme_from_settings(Path(folder) / "settings.json")


def read_source(source):
    """A theme folder, a settings file, a theme.json or a draft, as a theme dict."""
    src = Path(source)
    if src.is_dir():
        src = src / "settings.json"
    if not src.is_file():
        raise StandError(f"{src}: not found.")
    if src.name == "settings.json" or src.name.endswith(".settings.json"):
        return theme_from_settings(src)
    data = files.read_json_file(src)
    if not isinstance(data, dict) or "verbs" not in data:
        raise StandError(f"{src}: not a settings file, a theme folder or a theme.json.")
    return {k: data.get(k, "" if k in TEXT_KEYS else []) for k in KEYS}


def load_draft(args):
    if args.file and args.from_:
        raise StandError("Use --file or --from, not both.")
    if args.from_:
        return read_theme(THEMES.resolve(args.from_).path)
    if args.file:
        return read_source(args.file)
    raise StandError("Give a draft with --file <path>, or copy one with --from <name>.")


def checked(theme):
    theme = normalize(theme)
    bad = problems(theme)
    if bad:
        raise StandError("The theme has problems, so nothing was saved:\n"
                         + "\n".join(f"  - {b}" for b in bad))
    return theme


def create(name, args):
    THEMES.check_new_name(name)
    saved = checked(load_draft(args))
    stamp, lines = files.apply_changes(
        item_changes(THEMES.path_for("yours", name), saved, backup=False), args.dry_run)
    return items.write_result(f"Saved theme '{name}'.", stamp, lines, args.dry_run)


def update(name, args):
    entry = THEMES.require_yours(name)
    if args.from_:
        raise StandError("update takes --file only.")
    saved = checked(load_draft(args))
    stamp, lines = files.apply_changes(item_changes(entry.path, saved, backup=True), args.dry_run)
    message = f"Updated theme '{name}'."
    if active_name() == name:
        message += " It is active: run apply again to use the changes."
    return items.write_result(message, stamp, lines, args.dry_run)


def delete(name, dry_run):
    if active_name() == name:
        raise StandError(f"'{name}' is the active theme, so turn it off first: stand.py theme off")
    stamp, lines = THEMES.delete(name, dry_run)
    return items.write_result(f"Deleted theme '{name}'.", stamp, lines, dry_run)


def show(name):
    entry = THEMES.resolve(name)
    saved = read_theme(entry.path)
    lines = [f"{key}: {len(saved[key])}, for example: {', '.join(map(str, saved[key][:3]))}"
             for key in ("verbs", "announcements", "tips", "names")]
    return Result(f"{saved['display']} ({entry.source}), tips label: {saved['tipsLabel']}", lines, saved)


def check(names):
    targets = names or [e.name for e in THEMES.entries()]
    lines, ok = [], True
    for name in targets:
        found = problems(read_theme(THEMES.resolve(name).path))
        if found:
            ok = False
            lines.append(f"{name}:")
            lines += [f"  - {p}" for p in found]
        else:
            lines.append(f"{name}: OK")
    return Result("Checked themes.", lines, ok=ok)


def read(source):
    saved = read_source(source)
    return Result(f"Read {source}.", [json.dumps(saved, ensure_ascii=False, indent=2)], saved)


def export(name, args):
    entry = THEMES.resolve(name)
    if not args.to:
        raise StandError("Give a target folder with --to <folder>.")
    target = Path(args.to)
    if target.exists() and any(target.iterdir()):
        raise StandError(f"{target} is not empty.")
    stamp, lines = files.apply_changes(
        item_changes(target, read_theme(entry.path), backup=False), args.dry_run)
    return items.write_result(f"Exported '{name}' to {target}.", stamp, lines, args.dry_run)


SETTINGS_KEYS = ("spinnerVerbs", "companyAnnouncements", "spinnerTipsOverride")


def active_root():
    return paths.data_dir() / "active" / "theme"


def active_name():
    """The active theme, read from the real settings file: the tips file path names it.

    A restore or a hand edit changes the settings file, so this never trusts state.json.
    """
    tips_file = claude_settings.as_dict(claude_settings.load().get("spinnerTipsOverride")).get("tipsFile")
    if not isinstance(tips_file, str):
        return None
    where = Path(tips_file)
    if where.name == "tips.json" and where.parent.parent == active_root():
        return where.parent.name
    return None


def texts(value):
    return [v for v in value if isinstance(v, str) and v.strip()] if isinstance(value, list) else []


def active_snapshot():
    """The active theme, read from settings.json and the active folder its tips file names.

    It needs no data folder, so a mod can call it. Anything not from a Stand active folder counts as none.
    """
    settings = claude_settings.load()
    tips_file = claude_settings.as_dict(settings.get("spinnerTipsOverride")).get("tipsFile")
    where = Path(tips_file) if isinstance(tips_file, str) else None
    if (where is None or where.name != "tips.json"
            or where.parent.parent.name != "theme" or where.parent.parent.parent.name != "active"):
        raise StandError("No Stand theme is active.")
    label = claude_settings.as_dict(settings.get("spinnerTipsOverride")).get("label")
    return {
        "name": where.parent.name,
        "label": label if isinstance(label, str) else "",
        "verbs": texts(claude_settings.as_dict(settings.get("spinnerVerbs")).get("verbs")),
        "announcements": texts(settings.get("companyAnnouncements")),
        "names": texts(files.read_json_file(where.parent / "names.json")),
    }


def apply(name, dry_run):
    entry = THEMES.resolve(name)
    chosen = read_theme(entry.path)
    bad = problems(chosen)
    if bad:
        raise StandError(f"'{name}' has problems, so nothing was changed:\n"
                         + "\n".join(f"  - {b}" for b in bad))
    folder = active_root() / name
    tips_file = folder / "tips.json"
    settings = claude_settings.load()
    settings["spinnerVerbs"] = {"mode": "replace", "verbs": chosen["verbs"]}
    settings["companyAnnouncements"] = chosen["announcements"]
    settings["spinnerTipsOverride"] = {"tipsFile": str(tips_file), "label": chosen["tipsLabel"]}
    changes = [
        Change(tips_file, dump_json(chosen["tips"], indent=1), backup=False),
        Change(folder / "names.json", dump_json(chosen["names"], indent=1), backup=False),
        Change(paths.settings_path(), dump_json(settings)),
    ]
    stamp, lines = files.apply_changes(changes, dry_run)
    if not dry_run:
        st = state.load()
        st["theme"] = name
        state.save(st)
    return items.write_result(f"Applied theme '{name}'. Restart Claude Code to see it.", stamp, lines, dry_run)


def off(dry_run):
    name = active_name()
    if name is None:
        return Result("No Stand theme is active. Nothing changed.")
    settings = claude_settings.load()
    for key in SETTINGS_KEYS:
        settings.pop(key, None)
    folder = active_root() / name
    changes = [
        Change(paths.settings_path(), dump_json(settings)),
        Change(folder / "tips.json", None, backup=False),
        Change(folder / "names.json", None, backup=False),
    ]
    stamp, lines = files.apply_changes(changes, dry_run)
    if not dry_run:
        st = state.load()
        st["theme"] = None
        state.save(st)
    return items.write_result("Off: the Stand theme was removed. Restart Claude Code.", stamp, lines, dry_run)


def hook_name(raw):
    """PreToolUse hook text. Never blocks a subagent: on any problem return None (print nothing).

    It only acts while a Stand theme is really active, judged from the settings file.
    """
    try:
        event = json.loads(raw)
        name = active_name()
        if not name or not isinstance(event, dict):
            return None
        names = files.read_json_file(active_root() / name / "names.json")
        if not isinstance(names, list):
            return None
        names = [n for n in names if isinstance(n, str) and n]
        if not names:
            return None
        tool_input = event.get("tool_input")
        tool_input = dict(tool_input) if isinstance(tool_input, dict) else {}
        tool_input["description"] = random.choice(names)
        return json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "updatedInput": tool_input,
                "updatedToolInput": tool_input,
            }
        }, ensure_ascii=False)
    except Exception:
        return None


def run(args):
    action, names = args.action, args.names
    if action == "list":
        return items.list_result(THEMES, lambda n: n == active_name())
    if action == "show":
        return show(items.one_name(action, names))
    if action == "check":
        return check(names)
    if action == "read":
        return read(items.one_name(action, names))
    if action == "create":
        return create(items.one_name(action, names), args)
    if action == "update":
        return update(items.one_name(action, names), args)
    if action == "delete":
        return delete(items.one_name(action, names), args.dry_run)
    if action == "export":
        return export(items.one_name(action, names), args)
    if action == "apply":
        return apply(items.one_name(action, names), args.dry_run)
    if action == "off":
        return off(args.dry_run)
    if action == "active":
        data = active_snapshot()
        return Result(f"Active Stand theme: {data['name']}.", [], data)
    raise StandError(items.unknown_action("theme", action))
