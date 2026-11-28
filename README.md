# claude-plugins

Claude Code themes, output styles, `CLAUDE.md` snippets, character bars, shell tools and architect mode. Four plugins in one marketplace.

## Install

Needs `python3`.

```
claude plugin marketplace add <path to this repo>
claude plugin install tovar-core@tovar
claude plugin install tovar-mods@tovar
claude plugin install tovar-shell@tovar
claude plugin install architect-mode@tovar
```

Then restart Claude Code. Versions and what changed are in [CHANGELOG.md](CHANGELOG.md).

## tovar-core

You make and change your own items through skills. A small program writes the files and backs them up first, so you never edit settings by hand.

| Command | What you can do |
|---|---|
| `/tovar-core:themes` | Make a theme of UI text (spinner verbs, startup lines, tips, subagent names), change one, import a settings file, apply, turn off, delete. |
| `/tovar-core:styles` | Make an output style (how Claude words answers), change, apply, turn off, delete. |
| `/tovar-core:memory` | Make snippets of your global `CLAUDE.md` (for example commit rules), enable, disable, reorder. |
| `/tovar-core:undo` | See what is active. Restore a backup. |

It ships examples: the Pokemon, Movies, Videogames, Memes, Pop culture and Super Smash Bros. themes, the ELI5 style and a plain-writing snippet. They are read-only. Copy one to make it yours ("start from an example"), then change your copy. A name you make hides an example with the same name.

### Sub-agent names

When a theme is applied, each sub-agent Claude starts gets a name from that theme's names list, without repeats until every name was used. Needs `python3`, and a restart after applying a theme.

## tovar-mods

Two lines above the prompt: a character for what Claude is doing (idle, working, a tool call failed), and after each turn a short narration in the character's own voice and color. Characters rotate in shuffled rounds, so nobody repeats until everyone has shown. Silent characters make their sounds, then think the summary on the next line.

| Setting in `/config` | What it does |
|---|---|
| Bar | Which bar shows: `smash-bros`, `legendary-birds` or off. |
| Narrate | Narration after each turn. Costs one small Haiku call per turn. |

| Bar | Characters |
|---|---|
| `smash-bros` | Super Smash Bros fighters: neutral when idle, heroes at work, villains after a failed tool call. |
| `legendary-birds` | Articuno idle, Zapdos working, Moltres after a failed tool call. |

Some bars come as a pack with a theme on the same subject, checked so the spinner verbs never repeat a bar character's thinking actions. For the full Super Smash Bros. pack, apply the `smash-bros` theme with `/tovar-core:themes` and pick the `smash-bros` bar.

`/tovar-mods:narrate` recaps the whole session. Each character's voice, emoji and color live in their own profile file: edit it to change how they talk, then run `/reload-plugins` to apply it.

### Making a bar or a pack

Open Claude Code in this repo and ask for a bar ("make a Zelda bar") or a pack ("make a Zelda pack", a theme and a matching bar, checked so the spinner verbs never repeat the bar). The `tovar-new-bar` and `tovar-new-pack` skills plan it with you and build it. By hand:

```
python3 tools/tovar-mods.py new zelda   # scaffold from tovar-bar-template
# fill in tovar-mods/bars/zelda/roster.ts and one profile per character in characters/
python3 tools/tovar-mods.py check zelda                       # roster, profiles, checker, tests
python3 tools/tovar-mods.py overlap zelda zelda               # theme verbs vs the bar
python3 tools/tovar-mods.py register tovar-clock "What it does"   # list another plugin
```

A new bar is only data, so it shares the one engine. Pick it with the Bar setting, then run `/reload-plugins`.

## tovar-shell

Shell tools that take their look from your tovar theme. The first one is tmux: a clean config (clear active pane, status bar that lights up on the prefix) and a game-style menu.

`Ctrl+b` is the normal tmux prefix. A second `Ctrl+b` opens the menu, drawn in a popup:

| Screen | What you do |
|---|---|
| Windows | Tiles of every window, each with a miniature of its panes. Arrow keys pick one, `Enter` jumps to it, `n` new, `r` rename, `x` close. |
| Panes | The real layout of the current window. Arrow keys move to the neighbouring pane, `Enter` makes it active, `\|` and `-` split, `z` zoom, `x` close. |
| Sessions | Tiles of every session with a miniature of its current window. `Enter` switches, `n` new, `r` rename, `x` close (asks first). |
| Layouts | A preview of each layout for this window's panes: side by side, stacked, big left, big top, tiled. `Enter` applies it, `r` rotates the panes. |
| Tools | Scratch terminal, system monitor, disk space, system log and listening ports, each in a popup over your work. Add your own in `~/.config/tmux/tovar-tools.json`. |
| System | Copy mode, reload config, send `Ctrl+b`, detach. |

Run `/tovar-shell:tmux` to apply a **skin**. A skin sets the colors, border, cursor and layout of the status bar and menu. A skin named like a tovar theme is picked when that theme is active:

| Skin | Look |
|---|---|
| `videogames` | SNES RPG: blue window, white frame, gold highlight, `▶` cursor. |
| `smash-bros` | Black with red and yellow, heavy frames. |
| `pokemon` | White rounded box, black text, red trim, arrow cursor. |
| `zelda` | Dark stone, gold frame, green highlight, triforce cursor. |
| `street-fighter` | Arcade black, yellow and red, boxed buttons. |
| `movies`, `memes`, `pop-culture`, `default` | Palettes for the other example themes and a neutral fallback. |

Applying a skin saves your existing `~/.tmux.conf` first, and `off` puts it back. The menu files live in `~/.config/tmux/tovar`. Your own tools file sits next to it and is never overwritten. For a theme without a skin, ask for one ("make a skin for my Star Wars theme"). Needs `python3` and `tmux` 3.2 or newer (for the popup).

```
python3 tovar-shell/scripts/tovar_shell.py tmux list                  # skins, the applied one and the theme match
python3 tovar-shell/scripts/tovar_shell.py tmux apply --dry-run       # follow the active theme, show the change
python3 tovar-shell/scripts/tovar_shell.py tmux create zelda2 --file draft.json
```

## architect-mode

Experts judge the work, you decide, and code changes only after your approval. The plugin blocks unapproved edits itself. Start it with `/architect-mode:architect`.

Details are in [architect-mode/README.md](architect-mode/README.md).

## Desktop app

| Part | In the Claude desktop app |
|---|---|
| Bars and sub-agent names | Load in local Code sessions when the plugins are installed at the user level from the terminal (steps above). The app's own Add marketplace button cannot add a local-folder marketplace. |
| Cloud sessions | Do not run local plugins. |
| Theme spinner verbs, startup lines, tips | Not yet confirmed whether the app shows them. |
| Output styles and `CLAUDE.md` snippets | Shared files, so both the terminal and the app read them. |
