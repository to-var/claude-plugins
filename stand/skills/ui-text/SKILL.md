---
name: ui-text
description: Use when the user wants to create, change, apply, turn off, import, export, delete or list Claude Code UI text sets, called themes (spinner verbs, startup lines, tips, subagent names), with Stand.
---

# Stand UI text

UI text is the wording Claude Code shows around your work: spinner verbs, startup lines, spinner tips and subagent names. A set of it is called a theme. One theme is active at a time.

Run every command as (this is `STAND` below):

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}"
```

Rules for every action:

- Never edit theme files, `settings.json` or the Stand data folder by hand. Only call the commands below.
- Claude writes the content itself. Never call `claude -p` or another model.
- Ask with AskUserQuestion, one step at a time. Put your suggestion first, marked "(Recommended)". The user can type their own answer with "Other".
- Before `apply` or `off`, run the command with `--dry-run`, show the change in plain words, and wait for a yes.
- After apply or off, tell the user to restart Claude Code.

## Start

If the user gave no request, ask "What do you want to do?" with these options: Create a theme, Change a theme, Apply a theme, Turn the theme off, Import or export, Delete a theme, List themes. If the request is clear ("make a Star Wars theme"), go straight to that action.

## List

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" theme list
```

`yours` are the user's own themes. `example` themes ship with Stand and are read-only. `*` marks the active one.

## Create

1. **Start point.** Ask: from scratch, or copy an example or one of your themes? For a copy, run `theme create <new-name> --from <name>`, then use "Change a theme" below.
2. **Topic.** Take it from the request. Ask only if it is unclear.
3. **Name.** Suggest a short name (lowercase letters, digits and hyphens, for example `star-wars`) and a display name ("Star Wars").
4. **Tips label.** Suggest 3 labels of 1-2 words in the theme's voice.
5. **Spinner verbs.** Ask if the user has extra context (tone, sub-topic, things to include or avoid). Offer 3 style directions built from that context and from `verbs.md` in this folder. Write 40 verbs in the chosen direction.
6. **Startup lines.** Ask for extra context the same way. Write 20 lines. At least one invites the user to type a task.
7. **Tips.** Ask for extra context the same way. Write 15 fun facts about the subject.
8. **Names.** Ask for extra context the same way. Write about 150 subagent names.
9. **Preview.** Show 5 items from each list. Ask if anything should change. Rewrite what they ask for, and repeat until they say it is good.

Skip a context question when the user already gave that context.

Content rules:

| Key | Rule |
|---|---|
| `display` | The display name. |
| `tipsLabel` | The tips label. |
| `verbs` | Exactly 40. "-ing" phrases, at most 30 characters, about working (thinking, searching, building) in the theme's voice. |
| `announcements` | Exactly 20 startup lines, at most 90 characters. |
| `tips` | Exactly 15 fun facts, at most 90 characters each. Do not write the plugin tips, Stand adds them. |
| `names` | At least 100, at most 20 characters each, no repeats. Fictional characters or mascots only, no private people. |

Prefer lines most fans would recognise over deep cuts.

Write the approved content as one JSON file with those six keys in the scratchpad directory (for example `draft.json`), then run:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" theme create <name> --file <draft.json>
```

If it prints problems, fix the draft and run it again until it saves. Then offer to apply it (see Apply).

## Change a theme

1. Read the theme (the theme is in `data`):

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" theme show <name> --json
```

2. If it is an example, first run `theme create <new-name> --from <example>` and change the copy.
3. Ask what to change ("add 30 names", "make the verbs funnier", "new tips label"). Rewrite only that part. Keep the limits above.
4. Write the whole theme (six keys, the tips without the 5 plugin tips) as a draft and run:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" theme update <name> --file <draft.json>
```

5. If the theme is active, say so and offer to apply it again.

## Apply and turn off

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" theme apply <name> --dry-run
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" theme apply <name>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" theme off --dry-run
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" theme off
```

Run the dry run first, show the change, and run the real command only after a yes. Every real run makes a backup. The user can undo with `/stand:undo`.

## Import and export

To turn a Claude settings file, a theme folder or a `theme.json` into a Stand theme:

1. Read it (the theme is in `data`):

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" theme read <source> --json
```

2. Fill any gap. A Claude settings file has no names, so write about 150 names with the user's context.
3. Write a draft and run `theme create <name> --file <draft.json>`.

To export a theme as a portable folder:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" theme export <name> --to <folder>
```

## Check

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" theme check
```

Lists problems for every theme. Fix each one and check again.

## Delete

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" theme delete <name> --dry-run
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" theme delete <name>
```

Show what would go and wait for a yes before the real run. An active theme cannot be deleted: turn it off first. Examples cannot be deleted. A delete makes a backup.
