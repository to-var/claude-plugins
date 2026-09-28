# Memes theme

Part of the tovar-themes family for Claude Code. Only one theme is active at
a time: turning this one on turns the others off.

| Command | What it does |
|---|---|
| `/tovar-themes-memes:on` | Backs up your settings, turns the other themes off, writes this theme's spinner verbs, startup lines and tips. Restart Claude Code afterwards. |
| `/tovar-themes-memes:off` | Removes this theme's values, only if this theme is the active one. |

Subagent names work as soon as the plugin is enabled. They stop when you
disable it.

## Editing

The content lives in `theme.json`. Change it, then run the "on" command
again.

Every other file here comes from the family template. Do not edit them here:
edit the template, then run `python3 tools/themes.py sync` from the
marketplace folder.

## Requirements

`python3`.
