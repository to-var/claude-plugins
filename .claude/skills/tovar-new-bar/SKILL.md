---
name: tovar-new-bar
description: Use when the user asks for a new bar in tovar-mods or a new mod in this marketplace, for example "make a Zelda bar", "a Star Wars bar like smash-bros" or "a mod that shows a clock above the prompt". Adds a new bar to tovar-mods from tovar-bar-template, or lists another tovar- plugin in the marketplace.
---

# New bar

The `tovar-mods` plugin holds the engine and every character bar. A bar is
only data: `tovar-mods/bars/<bar>/roster.ts` plus one profile per character in
`tovar-mods/bars/<bar>/characters/`. The user picks the active bar with the
Bar setting in `/config`. Any other kind of mod is its own plugin folder at
the repo root, listed in `.claude-plugin/marketplace.json`.

Ask every question with AskUserQuestion: put your suggestion first, marked
"(Recommended)", give each option its tradeoff, and leave room for the user's
own answer. Skip a question the request already answers.

## 1. Which kind of change

If the user also wants a tovar theme on the same subject, use the `tovar-new-pack`
skill instead: it builds both and keeps them from repeating each other.

- **Character bar** (like smash-bros), added to `tovar-mods`: two lines above the prompt. A character
  per state, a thinking action until their narration arrives, then 2 to 3
  sentences in their own voice and color after each turn, and `/tovar-mods:narrate` for
  a whole-session recap. Characters rotate in shuffled rounds per state: each
  shows once before any repeats, and never twice in a row. Silent characters
  make their sounds, then think the summary on the next line. Use the template:
  section 2.
- **Anything else** (a side panel, a status line entry, a tool-call guard, a
  slash command): load the `plugin-authoring` skill and follow it, but write
  the mod as a new plugin folder at the repo root here, not into its default
  folder. Its name must start with `tovar-` (`tovar-clock`). Give
  `plugin.json` an `"author": {"name": "Jose Tovar"}` so the checker shows no
  warning. Then list it:

  ```
  python3 tools/tovar-mods.py register <name> "<one-line description>"
  ```

  and go to section 4, plugin branch.

## 2. Character bar: plan the roster

1. **Subject and short name.** Take both from the request. The short name is
   lowercase letters, digits and hyphens (`zelda`).
2. **What each state means.** The three states are fixed; who fills them is
   not. Offer splits that fit the subject, for example:

   | State | When it shows | smash-bros used |
   |---|---|---|
   | `calm` | idle | neutral characters |
   | `working` | while Claude works | heroes |
   | `burning` | after a turn where a tool call failed | villains |

3. **Roster.** 3 to 10 characters per state, recognisable to most fans. More
   characters means longer rounds before anyone repeats. No real
   people: fictional characters or mascots only.

## 3. Character bar: build it

1. **Scaffold** from this folder (it copies `tovar-bar-template` into
   `tovar-mods/bars/<short-name>/` and adds the bar to the Bar setting):

   ```
   python3 tools/tovar-mods.py new <short-name>
   ```

2. **Roster** in `tovar-mods/bars/<short-name>/roster.ts`: replace the examples and
   delete the `TODO(tovar-new-bar)` line. Give each character `thinks`: 2 things they
   would do while waiting, 30 characters or fewer ("brooding on a cliff").
   These must not repeat the active tovar theme's spinner verbs.

3. **Profiles.** Delete the three example files in
   `tovar-mods/bars/<short-name>/characters/`. Write one
   file per character, named after the name in lowercase with every run of
   other characters turned into one hyphen (`King K. Rool` →
   `king-k-rool.md`). Keep the template's layout:

   | Line or section | Rule |
   |---|---|
   | `- **Emoji:**` | One emoji that reads as the character. |
   | `- **Color:**` | `#rrggbb` from the character's palette, with a short note (`#2e9e44 (Hero of Time green)`). Mid-tones only: it must read on dark and light terminals, so no near-black or near-white. |
   | `- **Series:**`, `- **Nature:**` | Where they come from; which state they fill. |
   | `- **Speaks:**` | `yes`, or `NO. Out loud, sounds only, never real words. Their thoughts go on the next line, in plain words.` |
   | Voice, On success, On errors | How they talk and react. |
   | Signature lines and sounds | Catchphrases; for a silent character, only the sounds they make out loud (the narrator writes their thoughts on the next line). |
   | Famous quotes | Real, well-known lines only. If unsure a quote is real, leave it out. |

4. **Check** until it prints OK:

   ```
   python3 tools/tovar-mods.py check <short-name>
   ```

   It checks the roster against the profiles and that the bar is listed, then
   runs the plugin checker and the tests of `tovar-mods`.

## 4. Finish

1. Add a row for the bar (or the plugin) to the matching table in
   `README.md`: what it shows and when, in one sentence.
2. Tell the user how to turn it on.
   - **Bar branch:** no install of its own. Open `/config`, pick the bar with
     the Bar setting, then run `/reload-plugins`. Only one bar is active at a
     time, so say which bar was on before. If they installed `tovar-mods`
     earlier, run `claude plugin marketplace update tovar` first.
   - **Plugin branch** (the "anything else" path):

     ```
     claude plugin marketplace update tovar
     claude plugin install <plugin>@tovar
     ```

     then `/reload-plugins`. Stop here: the next step is only for bars.
3. Bar branch only: offer a matching tovar theme on the same subject. If the user says yes,
   build it with the `tovar-core:themes` skill, then run
   `python3 tools/tovar-mods.py overlap <short-name> <theme>` and fix what it prints
   until it says OK.
