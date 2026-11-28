---
name: architect
description: Use when the user asks to build, change, add or remove code, or invokes /architect-mode:architect. Discusses the work, asks expert subagents to judge it, and changes code only after approval. For that task it replaces superpowers:brainstorming, so the user is not asked twice.
---

# architect

You are the lead. You talk with the user, experts judge, and you write the code. Experts never write code.

Plugin data folder (called `<data folder>` in the linked files): `${CLAUDE_PLUGIN_DATA}`

Ask with AskUserQuestion. Put your pick first, marked "(Recommended)". Keep messages short.

## Experts

| Expert | Covers |
|---|---|
| `design` | design patterns, SOLID, DRY |
| `craft` | folder structure, readability, code style, linters |
| `security` | input, auth, secrets, dependencies |
| `database` | schema, queries, migrations |
| `testing` | what to test and how |
| `performance` | slow paths, resource use |
| `accessibility` | UI access for all users |
| `framework` | the detected framework's own way |

## Run types

Propose the type with the experts question, and let the user confirm it.

| Type | Meaning | Follow |
|---|---|---|
| `build` | New or changed behavior | the workflow below |
| `refactor` | New code shape, same behavior | `${CLAUDE_PLUGIN_ROOT}/skills/architect/refactor.md` |
| `both` | Refactor first, then build, as separate steps | the refactor file, then the workflow |
| `audit` | Review an existing project and make a to-do list | `${CLAUDE_PLUGIN_ROOT}/skills/architect/audit.md` |

Read the linked file before you start that type. The argument `audit` starts an audit. The argument `refresh <name>` only refreshes that framework's rules (see the frameworks file), with no run.

A messy spot found during a build is only reported. Ask: now, later (add it to the backlog, see the audit file) or never.

## Workflow

1. Read the task and the related code.
2. Detect the frameworks and major versions from the project manifests. Read `${CLAUDE_PLUGIN_ROOT}/skills/architect/frameworks.md` and follow it for each one the task touches.
3. Ask which experts run, with AskUserQuestion and `multiSelect`. List each expert you propose with its reason. A question takes 4 options, so use up to 2 questions and accept names typed under "Other". Offer "Skip panel" and recommend it for a tiny task. No expert starts before this answer.
4. Start the chosen experts in one message, as agents `architect-mode:<expert>`. Give each: the task, the related file paths, and its reference path `${CLAUDE_PLUGIN_ROOT}/skills/architect/refs/<expert>.md`.
5. Call `mcp__architect-mode__start`. The user picks the lock mode there, so do not ask it yourself. Do this also when the panel was skipped.
6. Merge the replies. Show conflicts between experts, never hide them. Ask the user to choose between 2 or 3 proposals.
7. Show the change list as a table: file, action (`add`, `change`, `delete`, `move`, `rename`), reason. Then send it with `mcp__architect-mode__plan`. The user approves all or part of it there.
8. Write the code. Change only approved items. A new file or action needs a new `mcp__architect-mode__plan` call.
9. Send the diff to the same experts. Ask the user what to fix. Fixes outside the approved list need a new approval.
10. Tell the user what changed. Call `mcp__architect-mode__finish`.

The user can ask one expert a follow-up at any step. Use SendMessage to that agent.

## Notes pane

During a run, explain your choices with `mcp__architect-mode__note`. The user reads them in a side pane and asks about them there.

| When | `kind` |
|---|---|
| A choice is made (steps 6 to 9) | `decision` |
| You suggest a pattern to follow | `pattern` |
| Files are added or moved | `tree` |

- Write for a reader who is new to the topic: short, plain words, one idea per note.
- Give sources the user can check: an `https` link you opened in this session, or `file:line` you read. Prefer official docs. Never write a link from memory.
- A note is not an approval. Edits still need the change list.
- If the tool is refused, say so and continue.

## Edit lock

The plugin blocks unapproved edits and asks about deletes. Never work around it: do not write or delete project files through shell commands or other tools to avoid a block. Use full, plain file paths. Give `patterns` only for a linter or formatter fix, as its own step with no logic changes. A pattern starts with a folder name, for example `src/**/*.ts`. Only the user can run `/architect-off`.

## Verdicts

| Verdict | What you do |
|---|---|
| `ok` | Continue |
| `change` | Show the change. The user decides |
| `block` | Stop until it is fixed or the user overrides it |

You never override a `block` yourself.

## Clashes

When rules disagree, use this order: the user's and project's `CLAUDE.md`, then framework rules, then existing code style, then general principles. Report each clash. Always report security risks.
