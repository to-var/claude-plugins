"""Command line for the Stand engine."""
import argparse
import json
import os
import sys

from . import StandError, files, items, memory, paths, state, style, theme
from .result import Result

RESTORE_WARNING = ("Restore replaces the whole file(s) below, so edits made to them after the backup "
                   "are undone too.")

AREAS = {"theme": theme.run, "style": style.run, "memory": memory.run}


def build_parser():
    p = argparse.ArgumentParser(
        prog="stand.py",
        description="Stand: the only writer of your Stand files. Areas: theme, style, memory, "
                    "status, restore, hook.")
    p.add_argument("area", choices=["theme", "style", "memory", "status", "restore", "hook"])
    p.add_argument("action", nargs="?")
    p.add_argument("names", nargs="*")
    p.add_argument("--file", help="draft file, theme folder, settings file or theme.json")
    p.add_argument("--from", dest="from_", help="copy an existing item")
    p.add_argument("--to", help="target folder for export")
    p.add_argument("--dry-run", action="store_true", help="show the change, write nothing")
    p.add_argument("--json", action="store_true", help="print machine readable output")
    p.add_argument("--data", help="the Stand data folder (default: $CLAUDE_PLUGIN_DATA)")
    return p


def status():
    st = state.load()
    active_theme = theme.active_name()
    lines = [
        f"theme: {active_theme or 'none'}",
        f"style: {style.active_name() or 'none'}",
        f"memory: {', '.join(memory.enabled()) or 'none'}",
        f"data folder: {paths.data_dir()}",
        f"config folder: {paths.config_dir()}",
    ]
    return Result("Stand status.", lines, {**st, "theme": active_theme, "style": style.active_name(), "memory": memory.enabled()})


def restore_command(args):
    if not args.action:
        backups = files.list_backups()
        lines = [f"{b['name']}: {', '.join(b['files'])}" for b in backups] or ["(no backups yet)"]
        return Result("Backups, newest first. Restore one with: stand.py restore <name>", lines, backups)
    stamp, lines = files.restore(args.action, args.dry_run)
    lines = [RESTORE_WARNING] + lines
    return items.write_result(f"Restored backup {args.action}.", stamp, lines, args.dry_run)


def dispatch(args):
    if args.area == "status":
        return status()
    if args.area == "restore":
        return restore_command(args)
    if not args.action:
        raise StandError(f"Say what to do with {args.area}. Use one of: {', '.join(items.ACTIONS[args.area])}.")
    return AREAS[args.area](args)


def emit(result, as_json):
    if as_json:
        print(json.dumps({"message": result.message, "lines": result.lines, "data": result.data,
                          "ok": result.ok}, ensure_ascii=False, indent=2))
        return
    if result.message:
        print(result.message)
    for line in result.lines:
        print(line)


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.data:
        os.environ["CLAUDE_PLUGIN_DATA"] = args.data
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    if args.area == "hook":
        if args.action == "name":
            try:
                out = theme.hook_name(sys.stdin.buffer.read().decode("utf-8"))
            except Exception:
                out = None
            if out:
                print(out)
        return 0
    try:
        result = dispatch(args)
    except (StandError, OSError) as e:
        print(f"stand: {e}", file=sys.stderr)
        return 1
    emit(result, args.json)
    return 0 if result.ok else 1
