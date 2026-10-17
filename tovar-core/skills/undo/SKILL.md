---
name: undo
description: Use when the user wants to see what tovar has active, list tovar backups, or undo a tovar change by restoring a backup.
---

# tovar status and undo

Every tovar write makes a backup first. This skill shows what is active and restores a backup.

Rules:

- Never edit `settings.json`, `CLAUDE.md`, output style files or the tovar data folder by hand, and never copy backup files yourself. Only call the commands below.
- Before restoring, run the command with `--dry-run`, show the change in plain words, and wait for a yes.

## Status

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tovar.py" --data "${CLAUDE_PLUGIN_DATA}" status
```

Shows the active theme, the active style, the enabled memory snippets and the folders tovar uses. It reads the real files, so it is right even after a manual change.

## List backups

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tovar.py" --data "${CLAUDE_PLUGIN_DATA}" restore
```

Backups are listed newest first, each with the files it holds. Help the user pick by asking what they want to undo (the last theme change, the last `CLAUDE.md` change) and match it to a backup by time and file.

## Restore

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tovar.py" --data "${CLAUDE_PLUGIN_DATA}" restore <backup-name> --dry-run
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tovar.py" --data "${CLAUDE_PLUGIN_DATA}" restore <backup-name>
```

A restore also backs up the current files first, so it can be undone too. After a restore, run `status` and tell the user to restart Claude Code.
