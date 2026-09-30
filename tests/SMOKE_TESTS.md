# Stand skill smoke tests

Skills cannot be tested by a script. Run these by hand after a change to a skill.
Use a scratch config folder so nothing real changes:
`CLAUDE_CONFIG_DIR=/tmp/stand-try claude --plugin-dir stand`

## /stand:theme
1. Say "make a Pokemon-lite theme". Expect one question per step, each with a recommended option and a context question for verbs, lines, tips and names.
2. Reach the preview and ask for one change. Expect only that part to change.
3. Expect the draft to be saved with `theme create`. Run `/stand:theme` and list: the new theme shows as `yours`.
4. Apply it. Expect a dry run first, then a yes prompt, then a restart reminder.
5. Turn it off. Expect the same dry run and yes prompt.

## /stand:style
1. Create a style. Expect purpose, voice and rules questions, and a preview.
2. Apply and turn off. Expect the dry run, the yes prompt and a restart reminder.

## /stand:memory
1. Create a snippet, then enable it. Expect the dry run to show a diff of `CLAUDE.md` before anything is written.
2. Put your own text above the block in `CLAUDE.md`, then disable the snippet. Expect your text to stay.

## /stand:undo
1. Run status. Expect the theme, style and snippets to match the steps above.
2. Restore the backup from step 4 of the theme test. Expect a dry run, a yes prompt, and status to show no theme.
