# claude-plugins

Claude Code plugins by Jose Tovar: themes and an output style.

## Setup

Needs `python3`.

```
claude plugin marketplace add to-var/claude-plugins
claude plugin install <plugin>@tovar
```

Then restart Claude Code.

## Plugins

| Plugin | What it does | Turn on |
|---|---|---|
| `tovar-themes-pokemon` | Pokémon theme | `/tovar-themes-pokemon:on` |
| `tovar-themes-pop` | Pop culture theme | `/tovar-themes-pop:on` |
| `tovar-output-styles` | Output styles (ELI5) | `/output-style` |
| `tovar-setup` | Copies your setup to a new machine | `/tovar-setup:apply` |

## Themes

A theme changes the spinner verbs, startup lines, spinner tips and subagent names. One theme is active at a time.

| Command | Effect |
|---|---|
| `/tovar-themes-<name>:on` | Turns the theme on and every other theme off. Backs up your settings first. |
| `/tovar-themes-<name>:off` | Removes the theme's values from your settings. |

- Backups go to `~/.claude/tovar-themes/<theme>/`.
- Restart Claude Code after `on` or `off`.
- Enabling a theme from the plugin menu skips "on". The other themes then stay active.
- Claude Code reads these values only from settings files, so "on" writes to `settings.json`.
- While a theme is enabled, subagent starts do not ask for permission.

## Output styles

An output style changes how Claude writes its answers.

| Style | What it does |
|---|---|
| ELI5 | Short, plain answers in ASD-STE100 Simplified Technical English. |

Run `/output-style` and pick the style.

## Copying your setup

`tovar-setup` copies marketplaces, plugins, a few settings, the status line
command and chosen CLAUDE.md text from one machine to another. Nothing ships
until `/tovar-setup:capture` asks and you approve it, item by item.

| Command | What it does |
|---|---|
| `/tovar-setup:check` | Shows what would change, changes nothing |
| `/tovar-setup:apply` | Asks per group, then applies the ones you approve |
| `/tovar-setup:capture` | On your own machine: asks what to publish into `setup.json` |

Restart Claude Code after `apply`.

## Development

| Task | Command |
|---|---|
| New theme | `python3 tools/themes.py new star-wars "Star Wars"` |
| Check a theme | `python3 tools/themes.py check star-wars` |
| Update all themes from `template/` | `python3 tools/themes.py sync` |
| Run tests | `python3 -m unittest discover -s tests -v` |

- After `new`, fill in `themes/tovar-themes-<name>/theme.json`.
- Or open Claude Code here and ask: "make a Star Wars theme".
- `sync` never touches `theme.json`. It never deletes files either.
