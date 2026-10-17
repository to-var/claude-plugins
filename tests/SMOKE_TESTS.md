# tovar skill smoke tests

Skills cannot be tested by a script. Run these by hand after a change to a skill.
Use a scratch config folder so nothing real changes:
`CLAUDE_CONFIG_DIR=/tmp/tovar-try claude --plugin-dir tovar-core`

## /tovar-core:themes
1. Say "make a Pokemon-lite theme". Expect one question per step, each with a recommended option and a context question for verbs, lines, tips and names.
2. Reach the preview and ask for one change. Expect only that part to change.
3. Expect the draft to be saved with `theme create`. Run `/tovar-core:themes` and list: the new theme shows as `yours`.
4. Apply it. Expect a dry run first, then a yes prompt, then a restart reminder.
5. Turn it off. Expect the same dry run and yes prompt.

## /tovar-core:styles
1. Create a style. Expect purpose, voice and rules questions, and a preview.
2. Apply and turn off. Expect the dry run, the yes prompt and a restart reminder.

## /tovar-core:memory
1. Create a snippet, then enable it. Expect the dry run to show a diff of `CLAUDE.md` before anything is written.
2. Put your own text above the block in `CLAUDE.md`, then disable the snippet. Expect your text to stay.

## /tovar-core:undo
1. Run status. Expect the theme, style and snippets to match the steps above.
2. Restore the backup from step 4 of the theme test. Expect a dry run, a yes prompt, and status to show no theme.

## Sub-agent names
1. Apply a theme, restart, then ask Claude to start two sub-agents. Expect each to show a different name from the theme.

## tovar-mods
1. Install it, open `/config`, set Bar to `legendary-birds`, run `/reload-plugins`. Expect two lines above the prompt with a bird.
2. Finish a turn. Expect a short narration in that character's voice, then `/tovar-mods:narrate` for a recap.
3. Run `/compact`. Expect an idle character, the facts line "ran /compact", then a short summary of the command.
4. Ask Claude to ask you a question with a recommended option. Expect the character above the dialog, "is reading the question", then a short take on why the recommended option fits. With no recommended option, expect a short line for the moment instead.
5. Set Narrate off. Expect no narration after the next turn. Set Bar to off. Expect the lines to go away.

## Desktop app
1. Open a local Code session in the Claude desktop app. Expect the bar above the prompt.
2. Finish a turn. Expect a narration after it.
3. Start a sub-agent. Expect a theme name.
4. Note whether the theme's spinner verbs show.
