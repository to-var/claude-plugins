---
name: tmux
description: Use when the user wants to set up, restyle, list or remove the tovar tmux config and its game-style menu, or make a tmux skin for a theme, with tovar-shell.
---

# tovar tmux

tovar-shell writes a tmux config and a game-style menu (windows, panes, sessions and layouts shown as visual maps, plus a tools launcher). A **skin** sets the colors and the menu look. A skin has the same name as a tovar theme (`smash-bros`, `pokemon`), so the tmux look follows the theme that is active.

Run every command as (this is `SHELL` below):

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tovar_shell.py" --data "${CLAUDE_PLUGIN_DATA}"
```

Rules for every action:

- Never edit `~/.tmux.conf`, `~/.config/tmux/tovar` or the data folder by hand. Only call the commands below.
- Claude writes skin content itself. Never call `claude -p` or another model.
- Ask with AskUserQuestion, one step at a time. Put your suggestion first, marked "(Recommended)". The user can type their own answer with "Other".
- Before `apply` or `off`, run the command with `--dry-run`, show the change in plain words, and wait for a yes.
- This machine may have no screen. Never open a GUI. tmux runs in the terminal.

## Start

If the user gave no request, ask "What do you want to do?" with: Apply a skin, Make a skin, Turn it off, List skins. If the request is clear ("use the pokemon look"), go straight to that action.

## List and status

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tovar_shell.py" --data "${CLAUDE_PLUGIN_DATA}" tmux list
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tovar_shell.py" --data "${CLAUDE_PLUGIN_DATA}" tmux status
```

`list` marks the skin that is applied (`*`) and the one that matches the active tovar theme (`~`). `status` says what is applied and what skin the active theme suggests.

## Apply

1. Run `tmux status`. If a skin matches the active theme, suggest it first ("Recommended"). Otherwise suggest `default`. Offer a few other skins from `tmux list`.
2. Dry run, and show the change in plain words:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tovar_shell.py" --data "${CLAUDE_PLUGIN_DATA}" tmux apply <skin> --dry-run
```

3. After a yes, run it again without `--dry-run`, adding `--reload` so a running tmux picks it up. Leave the skin name out to follow the active theme.
4. If the user already had a `~/.tmux.conf`, say it was saved first and that `tmux off` brings it back.

Tell the user how it works: `Ctrl+b` is the normal prefix, and a second `Ctrl+b` opens the menu (Windows, Panes, Sessions, Layouts, Tools, System). Arrow keys move, `Enter` picks, `Esc` goes back. The Tools screen can also list the user's own commands from `~/.config/tmux/tovar-tools.json` (see below).

When the user applies a new tovar theme later, offer to apply the matching skin too.

## Make a skin

A skin for a theme that has none (a theme you made, or any subject). Start from an existing one:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tovar_shell.py" --data "${CLAUDE_PLUGIN_DATA}" tmux show <skin>
```

1. **Name.** The theme's name (lowercase letters, digits, hyphens), so it is picked automatically when the theme is active.
2. **Look.** Ask about the game's menu UI: the main colors, the frame style, the cursor. Suggest a layout: `buttons` (a boxed button per item, like Final Fantasy or Street Fighter) or `list` (one box with a cursor, like the Pokemon or Zelda menus).
3. **Write the draft** as JSON in the scratchpad directory (for example `draft.json`), keys below, then run:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tovar_shell.py" --data "${CLAUDE_PLUGIN_DATA}" tmux create <name> --file <draft.json>
```

If it prints problems, fix the draft and run it again. Then offer to apply it.

| Key | Rule |
|---|---|
| `display` | The display name. |
| `colors.*` | `bg`, `text`, `dim`, `accent`, `accent2`, `ink`, `select_bg`, `select_fg`, `head`, each a 256-color number 0-255. `ink` is the text on top of `accent` and `accent2`. `status_bg` is optional (default `bg`). Keep `text` readable on `bg`, and `select_fg` readable on `select_bg`. |
| `menu.layout` | `buttons` or `list`. |
| `menu.border`, `menu.border_selected` | `single`, `double`, `rounded` or `heavy`. |
| `menu.cursor` | 1 or 2 characters, for example `▶`, `▲`, `★`. |
| `menu.title`, `menu.title_format` | Title text (at most 20 characters) and a format that contains `{}`, for example `▲  {}  ▲`. |
| `menu.spaced`, `menu.upper` | Space the title letters out, and upper-case labels. |
| `menu.rule` | The one character drawn as the title and footer line. |
| `tmux.pane_lines` | `single`, `double` or `heavy`. |

Look at a finished skin first (`tmux show smash-bros`) and keep to its shape.

## Add your own tools

The Tools screen shows a scratch terminal, a system monitor, disk space, the system log and listening ports. The user can add more in `~/.config/tmux/tovar-tools.json`, a JSON list. It is the user's file, so `apply` and `off` never touch it. Write it for them if they ask, and keep what is already in it:

```
[
  {"name": "Plex log", "command": "tail -f /var/lib/plexmediaserver/Library/Application\\ Support/Plex\\ Media\\ Server/Logs/Plex\\ Media\\ Server.log"},
  {"name": "Media space", "command": "du -sh /srv/media/*", "pause": true}
]
```

`pause: true` keeps the popup open until Enter, for commands that print and exit.

## Turn off

Dry run, a yes, then:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tovar_shell.py" --data "${CLAUDE_PLUGIN_DATA}" tmux off
```

It puts the user's earlier `~/.tmux.conf` back (or removes the managed one) and deletes `~/.config/tmux/tovar`. Tell the user to restart tmux (`tmux kill-server` ends every session, so let them choose when).
