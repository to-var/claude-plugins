---
name: undo
description: Use when the user wants to see what Stand has active, list Stand backups, or undo a Stand change by restoring a backup.
---

# Stand status and undo

Every Stand write makes a backup first. This skill shows what is active and restores a backup.

Rules:

- Never edit `settings.json`, `CLAUDE.md`, output style files or the Stand data folder by hand, and never copy backup files yourself. Only call the commands below.
- Before restoring, run the command with `--dry-run`, show the change in plain words, and wait for a yes.

## Status

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" status
```

Shows the active theme, the active style, the enabled memory snippets and the folders Stand uses. It reads the real files, so it is right even after a manual change.

## List backups

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" restore
```

Backups are listed newest first, each with the files it holds. Help the user pick by asking what they want to undo (the last theme change, the last `CLAUDE.md` change) and match it to a backup by time and file.

## Restore

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" restore <backup-name> --dry-run
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" restore <backup-name>
```

A restore also backs up the current files first, so it can be undone too. After a restore, run `status` and tell the user to restart Claude Code.
