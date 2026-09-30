---
name: output-style
description: Use when the user wants to create, change, apply, turn off, delete or list Claude Code output styles (how Claude words its answers) with Stand.
---

# Stand output styles

An output style changes how Claude writes its answers. One Stand style is active at a time.

Run every command as (this is `STAND` below):

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}"
```

Rules for every action:

- Never edit style files, `settings.json`, `~/.claude/output-styles` or the Stand data folder by hand. Only call the commands below.
- Claude writes the style itself. Never call `claude -p` or another model.
- Ask with AskUserQuestion, one step at a time. Put your suggestion first, marked "(Recommended)". The user can type their own answer with "Other".
- Before `apply` or `off`, run the command with `--dry-run`, show the change in plain words, and wait for a yes.
- After apply or off, tell the user to restart Claude Code.

## Start

If the user gave no request, ask "What do you want to do?" with these options: Create a style, Change a style, Apply a style, Turn the style off, Delete a style, List styles. If the request is clear, go straight to that action.

## List

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" style list
```

## Create

1. **Start point.** From scratch, or copy an example or one of your styles (`style create <new-name> --from <name>`, then "Change a style").
2. **Name.** Suggest a short name (lowercase letters, digits and hyphens) and a display name.
3. **Purpose.** Ask what the style is for (quick decisions, teaching, code review, a certain voice). Suggest 3 purposes.
4. **Voice.** Ask about tone, sentence length and vocabulary. Suggest 3 voices.
5. **Rules.** Ask for extra rules (formats, things to avoid, how to end an answer). Suggest 3 sets.
6. **Keep the coding instructions?** Recommended: yes (`keep-coding-instructions: true`), so Claude keeps its coding behaviour.
7. **Preview.** Show the whole style. Ask if anything should change and repeat until they say it is good.

Write the style as a Markdown file in the scratchpad directory (for example `draft.md`) in this shape:

```markdown
---
name: <Display name>
description: <one line, what it is for>
keep-coding-instructions: true
---

<the instructions, written to Claude in the second person or as plain rules>
```

Then run:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" style create <name> --file <draft.md>
```

If it prints problems, fix the draft and run it again. Then offer to apply it.

## Change a style

1. Run `style show <name>` and read the text. If it is an example, first run `style create <new-name> --from <example>`.
2. Ask what to change. Rewrite only that part.
3. Write the whole file as a draft and run:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" style update <name> --file <draft.md>
```

4. If the style is active, offer to apply it again.

## Apply and turn off

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" style apply <name> --dry-run
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" style apply <name>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" style off --dry-run
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" style off
```

Run the dry run first, show the change, and run the real command only after a yes. Every real run makes a backup. The user can undo with `/stand:undo`.

## Check

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" style check
```

## Show

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" style show <name>
```

## Delete

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" style delete <name> --dry-run
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" style delete <name>
```

Show what would go and wait for a yes before the real run. An active style cannot be deleted: turn it off first. Examples cannot be deleted. A delete makes a backup.
