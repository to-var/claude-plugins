"""Safe file writes: backups, atomic swaps, dry runs and restore."""
import difflib
import json
import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from . import StandError, paths


@dataclass
class Change:
    path: Path
    text: "str | None"      # None deletes the file
    backup: bool = True     # save the old file (and note new ones) so restore can undo


def read_text(path):
    path = Path(path)
    if not path.is_file():
        return None
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def read_json_file(path):
    text = read_text(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise StandError(f"{path} is not valid JSON, so nothing was changed.\n  {e}")


def dump_json(data, indent=2):
    return json.dumps(data, ensure_ascii=False, indent=indent) + "\n"


def atomic_write(path, text):
    # Write a temp file beside the real one, then swap it in, so a crash never leaves
    # a half-written file. Resolve first to keep a symlink intact.
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target = target.resolve()
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        if target.exists():
            shutil.copymode(target, tmp)
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def backups_root():
    return paths.data_dir() / "backups"


def new_backup_dir():
    stamp = time.strftime("%Y%m%d-%H%M%S")
    folder = backups_root() / stamp
    n = 1
    while folder.exists():
        n += 1
        folder = backups_root() / f"{stamp}-{n}"
    folder.mkdir(parents=True)
    return folder


def diff_lines(path, before, after):
    diff = list(difflib.unified_diff(
        (before or "").splitlines(), (after or "").splitlines(),
        fromfile=f"{path} (now)", tofile=f"{path} (after)" if after is not None else "(deleted)",
        lineterm="",
    ))
    if len(diff) > 80:
        diff = diff[:80] + [f"... {len(diff) - 80} more lines"]
    return diff


def apply_changes(changes, dry_run=False):
    """Write every change. Returns (backup name or None, report lines)."""
    todo = []
    for change in changes:
        before = read_text(change.path)
        if before != change.text:
            todo.append((change, before))

    if dry_run:
        lines = []
        for change, before in todo:
            lines += diff_lines(change.path, before, change.text)
        return None, lines

    saved, created, folder = {}, [], None
    for change, before in todo:
        if not change.backup:
            continue
        if folder is None:
            folder = new_backup_dir()
        if before is None:
            created.append(str(change.path))
        else:
            name = f"{len(saved) + 1}-{Path(change.path).name}"
            shutil.copyfile(change.path, folder / name)
            saved[name] = str(change.path)
    if folder is not None:
        atomic_write(folder / "manifest.json", dump_json({"files": saved, "created": created}))

    lines = []
    for change, _ in todo:
        if change.text is None:
            Path(change.path).unlink(missing_ok=True)
            lines.append(f"Deleted {change.path}")
        else:
            atomic_write(change.path, change.text)
            lines.append(f"Wrote {change.path}")
    return (folder.name if folder else None), lines


def list_backups():
    root = backups_root()
    if not root.is_dir():
        return []
    found = []
    for folder in sorted(root.iterdir(), reverse=True):
        manifest = read_json_file(folder / "manifest.json") if folder.is_dir() else None
        if manifest:
            found.append({"name": folder.name,
                          "files": list(manifest["files"].values()) + manifest["created"]})
    return found


def restore(name, dry_run=False):
    if Path(name).name != name:
        raise StandError(f"'{name}' is not a backup name.")
    folder = backups_root() / name
    manifest = read_json_file(folder / "manifest.json")
    if manifest is None:
        raise StandError(f"No backup named '{name}'. Run: stand.py restore")
    changes = [Change(Path(original), read_text(folder / saved))
               for saved, original in manifest["files"].items()]
    changes += [Change(Path(p), None) for p in manifest["created"]]
    return apply_changes(changes, dry_run)
