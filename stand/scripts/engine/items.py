"""Areas hold items in two places: yours (data folder) and examples (plugin folder)."""
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from . import StandError, files, paths
from .files import Change
from .result import Result

NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

ACTIONS = {
    "theme": ("list", "show", "check", "read", "create", "update", "delete", "export", "apply", "off"),
    "style": ("list", "show", "check", "create", "update", "delete", "apply", "off"),
    "memory": ("list", "show", "check", "create", "update", "delete", "enable", "disable", "order", "apply"),
}


@dataclass
class Entry:
    name: str
    source: str        # "yours" or "example"
    path: Path


class Area:
    """One kind of item. folder=True: a folder holding `marker`. Otherwise `<name>.md`."""

    def __init__(self, key, folder, marker="settings.json"):
        self.key, self.folder, self.marker = key, folder, marker

    def root(self, source):
        base = paths.data_dir() if source == "yours" else paths.examples_dir()
        return base / self.key

    def path_for(self, source, name):
        root = self.root(source)
        return root / name if self.folder else root / f"{name}.md"

    def _names(self, source):
        root = self.root(source)
        if not root.is_dir():
            return []
        if self.folder:
            return sorted(p.name for p in root.iterdir() if (p / self.marker).is_file())
        return sorted(p.stem for p in root.glob("*.md"))

    def entries(self):
        found = {n: Entry(n, "example", self.path_for("example", n)) for n in self._names("example")}
        found.update({n: Entry(n, "yours", self.path_for("yours", n)) for n in self._names("yours")})
        return [found[n] for n in sorted(found)]

    def resolve(self, name):
        for entry in self.entries():
            if entry.name == name:
                return entry
        raise StandError(f"No {self.key} item named '{name}'. Run: stand.py {self.key} list")

    def check_new_name(self, name):
        if not NAME.match(name):
            raise StandError(f"'{name}' is not a valid name. Use lowercase letters, digits and hyphens.")
        if self.path_for("yours", name).exists():
            raise StandError(f"You already have an item named '{name}' in {self.key}.")

    def require_yours(self, name):
        entry = self.resolve(name)
        if entry.source != "yours":
            raise StandError(
                f"'{name}' is an example and cannot be changed. "
                f"Copy it first: stand.py {self.key} create <new-name> --from {name}"
            )
        return entry

    def copy(self, entry, name):
        dest = self.path_for("yours", name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if self.folder:
            shutil.copytree(entry.path, dest)
        else:
            shutil.copyfile(entry.path, dest)

    def delete(self, name, dry_run):
        entry = self.require_yours(name)
        targets = [p for p in sorted(entry.path.rglob("*")) if p.is_file()] if self.folder else [entry.path]
        stamp, lines = files.apply_changes([Change(p, None) for p in targets], dry_run)
        if not dry_run and self.folder:
            shutil.rmtree(entry.path, ignore_errors=True)
        return stamp, lines


def list_result(area, is_active):
    rows = [{"name": e.name, "source": e.source, "active": bool(is_active(e.name))}
            for e in area.entries()]
    lines = [f"{'*' if r['active'] else ' '} {r['name']}  ({r['source']})" for r in rows] or ["(none)"]
    return Result(f"{len(rows)} in {area.key}. * marks the active one.", lines, rows)


def one_name(action, names):
    if len(names) != 1:
        raise StandError(f"'{action}' needs exactly one name.")
    return names[0]


def write_result(message, stamp, lines, dry_run):
    if dry_run:
        head = "Dry run. Nothing was written. This would change:" if lines else "Dry run. Nothing would change."
        return Result(head, lines)
    extra = [f"Backup: {stamp} (undo with: stand.py restore {stamp})"] if stamp else []
    return Result(message, lines + extra)


def unknown_action(area, action):
    return f"Unknown {area} action '{action}'. Use one of: {', '.join(ACTIONS[area])}."
