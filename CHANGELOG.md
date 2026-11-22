# Changelog

Each plugin has its own version, set in its `.claude-plugin/plugin.json`. Entries are newest first, grouped by plugin. Versions follow [semantic versioning](https://semver.org). Releases are tagged `<plugin>-v<version>`, for example `tovar-shell-v1.0.0`.

History before this file is in `git log`.

## tovar-shell 1.0.0 (2026-11-22)

First release.

### Added
- A tmux config with a clear active pane and a status bar that lights up on the prefix.
- A game-style menu on a second `Ctrl+b`: Windows and Panes as visual maps picked with the arrow keys, plus a Session screen.
- Skins that set colors, border, cursor and layout of the status bar and menu: `default`, `videogames`, `smash-bros`, `pokemon`, `zelda`, `street-fighter`, `movies`, `memes`, `pop-culture`.
- The skin follows the active tovar theme, including themes applied by the older `tovar-themes-*` plugins.
- `/tovar-shell:tmux` to apply, restyle, list, turn off and make skins. An existing `~/.tmux.conf` is saved first and `off` restores it.

## tovar-mods 1.0.0 (2026-10-17)

First release.

### Added
- Character bars above the prompt: a character for what Claude is doing, then a narration of each turn in their own voice and color.
- The `smash-bros` and `legendary-birds` bars, and `/tovar-mods:narrate` for a session recap.

## tovar-core 2.2.0 (2026-10-17)

### Changed
- Renamed the plugin to `tovar-core`.

### Added
- Long ELI5 replies are chunked behind a continue question.
