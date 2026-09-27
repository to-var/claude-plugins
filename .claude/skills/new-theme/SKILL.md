---
name: new-theme
description: Use when the user asks for a new theme in the tovar-themes family, for example "make a Star Wars theme" or "add a Studio Ghibli theme". Scaffolds the plugin from the template and writes its content.
---

# New theme

1. **Subject and short name.** Take both from the request. The short name is
   lowercase letters, digits and hyphens (`star-wars`). Ask one question only
   if the subject is unclear.

2. **Scaffold.** From the marketplace folder, run:

   ```
   python3 tools/themes.py new <short-name> "<Display Name>"
   ```

3. **Write the content** in `themes/tovar-themes-<short-name>/theme.json`:

   | Key | Rule |
   |---|---|
   | `tipsLabel` | 1-2 words in the theme's voice ("Pokédex", "Trivia"). |
   | `verbs` | Exactly 40. "-ing" phrases, at most 30 characters, about working (thinking, searching, building) in the theme's voice. |
   | `announcements` | Exactly 20 startup lines, at most 90 characters. At least one invites the user to type a task. |
   | `tips` | Exactly 20. Keep the 5 the builder wrote, they explain the plugin. Add 15 fun facts about the subject, at most 90 characters each. |
   | `names` | At least 100 (about 150 is a good size) characters people recognise, at most 20 characters each, no repeats. Fictional characters only, or mascots, no private people. |
   | `_todo` | Delete this line. |

   Prefer lines most fans would recognise over deep cuts.

4. **Check.** Run `python3 tools/themes.py check <short-name>`. Fix every
   problem it lists and run it again until it prints OK.

5. **Tell the user** how to install and turn it on:

   ```
   claude plugin marketplace update tovar
   claude plugin install tovar-themes-<short-name>@tovar
   ```

   Then `/tovar-themes-<short-name>:on` and a restart of Claude Code.
