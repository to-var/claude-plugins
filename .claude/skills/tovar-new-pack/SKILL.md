---
name: tovar-new-pack
description: Use when the user asks for a pack, or for both a theme and a bar on one subject, for example "make a Zelda pack" or "a Star Wars theme and bar". Builds a tovar theme and a matching character bar that never repeat each other.
---

# New pack

A pack is a tovar theme (spinner verbs, startup lines, tips, subagent names)
plus a character bar (two lines above the prompt) on the same subject. The
two show at the same time, so they must split the work:

| Part | Owns | Never |
|---|---|---|
| Theme spinner verbs | Plain actions of the world ("Opening a chest", "Wavedashing") | Name a bar character |
| Bar thinking actions | What one character does while waiting ("brooding on a cliff") | Equal a spinner verb |

Ask every question with AskUserQuestion: your suggestion first, marked
"(Recommended)", a tradeoff per option, room for the user's own answer. Skip a
question the request already answers.

## 1. Plan

1. **Subject and short name.** One short name for both parts (`zelda`):
   lowercase letters, digits and hyphens.
2. **Bar.** Follow the `tovar-new-bar` skill, sections 2 (what each state means,
   the roster).
3. **Theme.** Ask for tone and anything to include or avoid, as the tovar
   theme skill does. Remind yourself of the split above before writing verbs.

## 2. Build

1. **Theme.** Load the `tovar-core:themes` skill and follow its Create steps with
   the plan above. Save it under the short name. Do not apply it yet.
2. **Bar.** Follow the `tovar-new-bar` skill, section 3, until
   `python3 tools/tovar-mods.py check <short-name>` prints OK.
3. **Overlap.** Run:

   ```
   python3 tools/tovar-mods.py overlap <short-name> <short-name>
   ```

   For each line it prints, reword the spinner verb (change the theme with
   the `tovar-core:themes` skill) or the thinking action (in the bar's roster).
   Run it again until it prints OK.

## 3. Finish

1. Follow the `tovar-new-bar` skill, section 4 (README row, pick the bar in /config, one bar
   on at a time).
2. Offer to apply the theme, using the Apply steps of the `tovar-core:themes`
   skill: dry run first, a yes, then the real run.
3. Tell the user to restart Claude Code: the theme only shows after a restart.
