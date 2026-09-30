---
name: memory
description: Use when the user wants to create, change, enable, disable, reorder, delete or list snippets of their global Claude Code CLAUDE.md with Stand.
---

# Stand memory

A memory snippet is a short piece of text for the user's global `CLAUDE.md` (for example "commit rules" or "writing style"). Stand keeps the enabled snippets in one marked block in `~/.claude/CLAUDE.md`. Text outside the block is never touched.

Run every command as (this is `STAND` below):

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}"
```

Rules for every action:

- Never edit `CLAUDE.md`, snippet files or the Stand data folder by hand. Only call the commands below.
- Claude writes the snippet itself. Never call `claude -p` or another model.
- Ask with AskUserQuestion, one step at a time. Put your suggestion first, marked "(Recommended)". The user can type their own answer with "Other".
- Before `enable`, `disable`, `order` or `apply`, run the command with `--dry-run`, show the change to `CLAUDE.md` in plain words, and wait for a yes.

## Start

If the user gave no request, ask "What do you want to do?" with these options: Create a snippet, Change a snippet, Enable a snippet, Disable a snippet, Reorder, Delete a snippet, List. If the request is clear, go straight to that action.

## List

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" memory list
```

`*` marks enabled snippets. `example` snippets ship with Stand and are read-only.

## Create

1. **Start point.** From scratch, or copy an example or one of your snippets (`memory create <new-name> --from <name>`, then "Change a snippet").
2. **Topic.** Ask what it covers. Suggest 4 topics: writing style, commit rules, pull request rules, tool preferences.
3. **Name.** Suggest a short name (lowercase letters, digits and hyphens).
4. **Rules.** Ask for the rules in the user's own words. Turn them into short, direct lines. Keep it as short as it can be: every line costs context in every session.
5. **Preview.** Show the snippet. Ask if anything should change and repeat until they say it is good.

The text must not contain `<!-- stand:` markers and must not be empty. Write it as a Markdown file in the scratchpad directory (for example `draft.md`), then run:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" memory create <name> --file <draft.md>
```

Then offer to enable it.

## Change a snippet

1. Run `memory show <name>`. If it is an example, first run `memory create <new-name> --from <example>`.
2. Ask what to change. Rewrite only that part.
3. Write the whole text as a draft and run:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" memory update <name> --file <draft.md>
```

4. If the snippet is enabled, the block in `CLAUDE.md` is now out of date. Preview and run `memory apply` (see below).

## Enable, disable, reorder, apply

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" memory enable <name> --dry-run
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" memory enable <name>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" memory disable <name>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" memory order <first> <second> <third>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" memory apply
```

Run the dry run first, show the diff, and run the real command only after a yes. `order` must list exactly the enabled snippets. Every real run backs up `CLAUDE.md`. The user can undo with `/stand:undo`. If Stand reports a broken block (one marker missing), stop and ask the user to fix the `<!-- stand:... -->` lines.

## Check

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" memory check
```

## Show

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" memory show <name>
```

## Delete

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" memory delete <name> --dry-run
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stand.py" --data "${CLAUDE_PLUGIN_DATA}" memory delete <name>
```

Show what would go and wait for a yes before the real run. An enabled snippet cannot be deleted: disable it first. Examples cannot be deleted. A delete makes a backup.
