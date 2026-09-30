"""Style area: output styles Stand writes into the config folder."""
from pathlib import Path

from . import StandError, claude_settings, files, items, paths, state
from .files import Change, dump_json
from .result import Result

STYLES = items.Area("styles", folder=False)
OUTPUT_STYLE_KEY = "outputStyle"     # confirmed in the Task 1 notes


def parse_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            meta = {}
            for line in lines[1:end]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip()] = value.strip().strip("\"'")
            return meta, "\n".join(lines[end + 1:])
    return {}, text


def problems(text):
    meta, body = parse_frontmatter(text)
    found = [f"frontmatter {key} is missing" for key in ("name", "description") if not meta.get(key)]
    if not body.strip():
        found.append("the style has no instructions")
    return found


def target(name):
    return paths.styles_dir() / f"stand-{name}.md"


def active_name():
    """The active Stand style: the stand-*.md file whose frontmatter name is the current outputStyle."""
    current = claude_settings.load().get(OUTPUT_STYLE_KEY)
    if not isinstance(current, str) or not paths.styles_dir().is_dir():
        return None
    for path in sorted(paths.styles_dir().glob("stand-*.md")):
        if parse_frontmatter(files.read_text(path) or "")[0].get("name") == current:
            return path.stem[len("stand-"):]
    return None


def read_draft(args):
    if args.file and args.from_:
        raise StandError("Use --file or --from, not both.")
    if args.from_:
        return files.read_text(STYLES.resolve(args.from_).path)
    if args.file:
        text = files.read_text(args.file)
        if text is None:
            raise StandError(f"{args.file}: not found.")
        return text
    raise StandError("Give a draft with --file <path>, or copy one with --from <name>.")


def checked(text):
    bad = problems(text)
    if bad:
        raise StandError("The style has problems, so nothing was saved:\n"
                         + "\n".join(f"  - {b}" for b in bad))
    return text


def create(name, args):
    STYLES.check_new_name(name)
    text = checked(read_draft(args))
    stamp, lines = files.apply_changes([Change(STYLES.path_for("yours", name), text, backup=False)], args.dry_run)
    return items.write_result(f"Saved style '{name}'.", stamp, lines, args.dry_run)


def update(name, args):
    entry = STYLES.require_yours(name)
    if args.from_:
        raise StandError("update takes --file only.")
    text = checked(read_draft(args))
    stamp, lines = files.apply_changes([Change(entry.path, text)], args.dry_run)
    message = f"Updated style '{name}'."
    if active_name() == name:
        message += " It is active: run apply again to use the changes."
    return items.write_result(message, stamp, lines, args.dry_run)


def delete(name, dry_run):
    if active_name() == name:
        raise StandError(f"'{name}' is the active style, so turn it off first: stand.py style off")
    stamp, lines = STYLES.delete(name, dry_run)
    return items.write_result(f"Deleted style '{name}'.", stamp, lines, dry_run)


def show(name):
    entry = STYLES.resolve(name)
    text = files.read_text(entry.path)
    meta, _ = parse_frontmatter(text)
    return Result(f"{meta.get('name', name)} ({entry.source}): {meta.get('description', '')}",
                  text.splitlines(), text)


def check(names):
    targets = names or [e.name for e in STYLES.entries()]
    lines, ok = [], True
    for name in targets:
        found = problems(files.read_text(STYLES.resolve(name).path))
        if found:
            ok = False
            lines.append(f"{name}:")
            lines += [f"  - {p}" for p in found]
        else:
            lines.append(f"{name}: OK")
    return Result("Checked styles.", lines, ok=ok)


def apply(name, dry_run):
    entry = STYLES.resolve(name)
    text = files.read_text(entry.path)
    bad = problems(text)
    if bad:
        raise StandError(f"'{name}' has problems, so nothing was changed:\n"
                         + "\n".join(f"  - {b}" for b in bad))
    setting = parse_frontmatter(text)[0]["name"]
    settings = claude_settings.load()
    st = state.load()
    old = active_name()
    changes = []
    if old and old != name:
        changes.append(Change(target(old), None))
    settings[OUTPUT_STYLE_KEY] = setting
    changes += [Change(target(name), text), Change(paths.settings_path(), dump_json(settings))]
    stamp, lines = files.apply_changes(changes, dry_run)
    if not dry_run:
        st["style"], st["style_setting"] = name, setting
        state.save(st)
    return items.write_result(f"Applied style '{name}'. Restart Claude Code to use it.", stamp, lines, dry_run)


def off(dry_run):
    name = active_name()
    if name is None:
        return Result("No Stand style is active. Nothing changed.")
    settings = claude_settings.load()
    settings.pop(OUTPUT_STYLE_KEY, None)
    changes = [Change(target(name), None), Change(paths.settings_path(), dump_json(settings))]
    stamp, lines = files.apply_changes(changes, dry_run)
    if not dry_run:
        st = state.load()
        st["style"] = st["style_setting"] = None
        state.save(st)
    return items.write_result("Off: the Stand style was removed. Restart Claude Code.", stamp, lines, dry_run)


def run(args):
    action, names = args.action, args.names
    if action == "list":
        return items.list_result(STYLES, lambda n: n == active_name())
    if action == "show":
        return show(items.one_name(action, names))
    if action == "check":
        return check(names)
    if action == "create":
        return create(items.one_name(action, names), args)
    if action == "update":
        return update(items.one_name(action, names), args)
    if action == "delete":
        return delete(items.one_name(action, names), args.dry_run)
    if action == "apply":
        return apply(items.one_name(action, names), args.dry_run)
    if action == "off":
        return off(args.dry_run)
    raise StandError(items.unknown_action("style", action))
