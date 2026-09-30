# claude-plugins

Claude Code plugins by Jose Tovar.

## Setup

Needs `python3`.

```
claude plugin marketplace add to-var/claude-plugins
claude plugin install stand@tovar
```

Then restart Claude Code.

## Plugins

| Plugin | What it does |
|---|---|
| `stand` | Personalize Claude Code: themes, output styles and global `CLAUDE.md` snippets. |
| `tovar-setup` | Copies your setup to a new machine (`/tovar-setup:apply`). Will move into Stand later. |

## Stand

Stand changes how Claude Code looks and behaves. You make and change your own items through skills. A small program writes the files and backs them up first, so you never edit settings by hand.

| Skill | What you can do |
|---|---|
| `/stand:theme` | Make a theme (spinner verbs, startup lines, tips, subagent names), change one, import a settings file, apply, turn off, delete. |
| `/stand:style` | Make an output style (how Claude words answers), change, apply, turn off, delete. |
| `/stand:memory` | Make snippets of your global `CLAUDE.md` (for example commit rules), enable, disable, reorder. |
| `/stand:undo` | See what is active. Restore a backup. |

Stand ships examples: the Pokémon, Movies, Videogames and Memes themes, the ELI5 style and a plain-writing snippet. They are read-only. Copy one to make it yours ("start from an example"), then change your copy. A name you make hides an example with the same name.

## Where things live

- Your items: the plugin data folder (`${CLAUDE_PLUGIN_DATA}`). Plugin updates never overwrite it. Do not edit it by hand.
- Backups: `backups/` in that folder. Every write makes one. `/stand:undo` restores it.
- Stand writes results into the places Claude Code reads:

| Area | Written to |
|---|---|
| Theme | `spinnerVerbs`, `companyAnnouncements`, `spinnerTipsOverride` in `~/.claude/settings.json` |
| Style | `~/.claude/output-styles/stand-<name>.md` and `outputStyle` in `settings.json` |
| Memory | A block between `<!-- stand:start -->` and `<!-- stand:end -->` in `~/.claude/CLAUDE.md`. Text outside it is never touched. |

- Restart Claude Code after a theme or style change.
- While a theme is active, subagent starts do not ask for permission. The hook that names subagents allows the start.
- `/plugin uninstall` asks before deleting your Stand data. To keep a theme, export it first: `/stand:theme`, then "Import or export".

## Moving from the old plugins

The `tovar-themes-*` and `tovar-output-styles` plugins are gone. To switch:

1. Run `/tovar-themes-<name>:off` for the active theme.
2. Uninstall the old plugins.
3. Run `claude plugin install stand@tovar`.
4. Run `/stand:theme` and pick an example.

## Development

```
cd tests && python3 -m unittest
```

`tests/SMOKE_TESTS.md` lists the manual checks for the skills.
