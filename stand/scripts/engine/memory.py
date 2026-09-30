"""Memory area: CLAUDE.md snippets that Stand keeps in one marked block."""
from . import StandError, files, items, paths, state
from .files import Change
from .result import Result

MEMORY = items.Area("memory", folder=False)
START = "<!-- stand:start -->"
END = "<!-- stand:end -->"
BROKEN = ("Your CLAUDE.md has a broken Stand block (a missing, repeated or misordered marker), "
          "so nothing was changed. Fix or remove the <!-- stand:... --> lines by hand, then try again.")


def problems(text):
    found = []
    if not text.strip():
        found.append("the snippet is empty")
    if "<!-- stand:" in text:
        found.append("the snippet must not contain <!-- stand: markers")
    return found


def render(snippets):
    """The block for (name, text) pairs, or None when there are none."""
    if not snippets:
        return None
    lines = [START]
    for name, text in snippets:
        lines += [f"<!-- stand:{name} -->", text.replace("\r\n", "\n").strip("\n"), ""]
    lines[-1] = END
    return "\n".join(lines)


def merge(existing, block):
    """New CLAUDE.md text with the block set (or removed when block is None). Outside text is kept."""
    text = existing or ""
    starts, ends = text.count(START), text.count(END)
    if starts != ends or starts > 1 or (starts == 1 and text.find(END) < text.find(START)):
        raise StandError(BROKEN)
    nl = "\r\n" if "\r\n" in text else "\n"
    if block is not None:
        block = block.replace("\n", nl)
    if starts == 1:
        s, e = text.find(START), text.find(END) + len(END)
        if block is not None:
            return text[:s] + block + text[e:]
        before, after = text[:s].rstrip("\r\n"), text[e:].lstrip("\r\n")
        rest = before + (nl * 2 if before and after else "") + after
        return rest.rstrip("\r\n") + nl if rest.strip() else ""
    if block is None:
        return existing
    if not text.strip():
        return block + nl
    return text.rstrip("\r\n") + nl * 2 + block + nl


def has_block():
    text = files.read_text(paths.claude_md_path()) or ""
    return START in text and END in text


def enabled():
    """The enabled snippets, judged from the real CLAUDE.md so a restore cannot fool it."""
    return list(state.load()["memory"]) if has_block() else []


def sync(names, dry_run, message):
    snippets = []
    for name in names:
        text = files.read_text(MEMORY.resolve(name).path)
        bad = problems(text)
        if bad:
            raise StandError(f"'{name}' has problems, so nothing was changed:\n"
                             + "\n".join(f"  - {b}" for b in bad))
        snippets.append((name, text))
    current = files.read_text(paths.claude_md_path())
    stamp, lines = files.apply_changes([Change(paths.claude_md_path(), merge(current, render(snippets)))], dry_run)
    if not dry_run:
        st = state.load()
        st["memory"] = list(names)
        state.save(st)
    return items.write_result(message, stamp, lines, dry_run)


def read_draft(args):
    if args.file and args.from_:
        raise StandError("Use --file or --from, not both.")
    if args.from_:
        return files.read_text(MEMORY.resolve(args.from_).path)
    if args.file:
        text = files.read_text(args.file)
        if text is None:
            raise StandError(f"{args.file}: not found.")
        return text
    raise StandError("Give a draft with --file <path>, or copy one with --from <name>.")


def checked(text):
    bad = problems(text)
    if bad:
        raise StandError("The snippet has problems, so nothing was saved:\n"
                         + "\n".join(f"  - {b}" for b in bad))
    return text


def create(name, args):
    MEMORY.check_new_name(name)
    text = checked(read_draft(args))
    stamp, lines = files.apply_changes([Change(MEMORY.path_for("yours", name), text, backup=False)], args.dry_run)
    return items.write_result(f"Saved snippet '{name}'.", stamp, lines, args.dry_run)


def update(name, args):
    entry = MEMORY.require_yours(name)
    if args.from_:
        raise StandError("update takes --file only.")
    text = checked(read_draft(args))
    stamp, lines = files.apply_changes([Change(entry.path, text)], args.dry_run)
    message = f"Updated snippet '{name}'."
    if name in enabled():
        message += " It is enabled: run apply to write the change into CLAUDE.md."
    return items.write_result(message, stamp, lines, args.dry_run)


def delete(name, dry_run):
    if name in enabled():
        raise StandError(f"'{name}' is enabled, so disable it first: stand.py memory disable {name}")
    stamp, lines = MEMORY.delete(name, dry_run)
    return items.write_result(f"Deleted snippet '{name}'.", stamp, lines, dry_run)


def show(name):
    entry = MEMORY.resolve(name)
    text = files.read_text(entry.path)
    return Result(f"{name} ({entry.source})", text.splitlines(), text)


def check(names):
    targets = names or [e.name for e in MEMORY.entries()]
    lines, ok = [], True
    for name in targets:
        found = problems(files.read_text(MEMORY.resolve(name).path))
        if found:
            ok = False
            lines.append(f"{name}:")
            lines += [f"  - {p}" for p in found]
        else:
            lines.append(f"{name}: OK")
    return Result("Checked snippets.", lines, ok=ok)


def enable(name, dry_run):
    MEMORY.resolve(name)
    now = enabled()
    if name in now:
        return Result(f"'{name}' is already enabled. Nothing changed.")
    return sync(now + [name], dry_run, f"Enabled '{name}' in CLAUDE.md.")


def disable(name, dry_run):
    now = enabled()
    if name not in now:
        return Result(f"'{name}' is not enabled. Nothing changed.")
    return sync([n for n in now if n != name], dry_run, f"Disabled '{name}' in CLAUDE.md.")


def order(names, dry_run):
    if sorted(names) != sorted(enabled()):
        raise StandError("List exactly the enabled snippets, each once. Enabled now: "
                         + (", ".join(enabled()) or "none"))
    return sync(names, dry_run, "Reordered the snippets in CLAUDE.md.")


def run(args):
    action, names = args.action, args.names
    if action == "list":
        return items.list_result(MEMORY, lambda n: n in enabled())
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
    if action == "enable":
        return enable(items.one_name(action, names), args.dry_run)
    if action == "disable":
        return disable(items.one_name(action, names), args.dry_run)
    if action == "order":
        return order(names, args.dry_run)
    if action == "apply":
        return sync(enabled(), args.dry_run, "Wrote the enabled snippets into CLAUDE.md.")
    raise StandError(items.unknown_action("memory", action))
