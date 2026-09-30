# claude-plugins

A framework to build your own Claude Code themes, output styles and `CLAUDE.md` snippets. It ships as one plugin, Stand.

## Setup

Needs `python3`.

```
claude plugin marketplace add to-var/claude-plugins
claude plugin install stand@tovar
```

Then restart Claude Code.

## Stand

A Stand is a spirit companion that fights beside its user and bends the world to their will. Here, your Stand rewrites how Claude Code looks and behaves, from its spinner verbs and startup lines to its output style and memory. Every change is backed up first, so like Bites the Dust, any bad move can be rewound, and you never touch a settings file yourself.

Stand changes how Claude Code looks and behaves. You make and change your own items through skills. A small program writes the files and backs them up first, so you never edit settings by hand.

| Skill | What you can do |
|---|---|
| `/stand:ui-text` | Make a theme of UI text (spinner verbs, startup lines, tips, subagent names), change one, import a settings file, apply, turn off, delete. |
| `/stand:output-style` | Make an output style (how Claude words answers), change, apply, turn off, delete. |
| `/stand:config-memory` | Make snippets of your global `CLAUDE.md` (for example commit rules), enable, disable, reorder. |
| `/stand:undo` | See what is active. Restore a backup. |

Stand ships examples: the Pokémon, Movies, Videogames and Memes themes, the ELI5 style and a plain-writing snippet. They are read-only. Copy one to make it yours ("start from an example"), then change your copy. A name you make hides an example with the same name.
