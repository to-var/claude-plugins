# architect-mode

Architect mode for Claude Code. You talk to one lead, experts judge the work, and code changes only after your approval.

## Why

To keep control of how code is added, changed and deleted.

## Install

```
claude plugin marketplace add to-var/claude-plugins
claude plugin install architect-mode@tovar
```

Then restart Claude Code.

## Use

```
/architect-mode:architect add rate limits to the login route
```

1. You pick the experts.
2. They judge the plan: `ok`, `change` or `block`.
3. You pick the lock mode.
4. You pick a proposal and approve the file list.
5. The lead writes the code. The experts check it.

## Refactor and audit

| Type | What happens |
|---|---|
| refactor | Same behavior, new shape. Tests run before and after each small step |
| both | Refactor first, then build |
| audit | `/architect-mode:architect audit` reviews an existing project and writes a ranked backlog. It changes no code |

The backlog lives in the plugin data folder, so findings stay private. A project's own instructions can move it into the repo.

## Edit lock

The plugin itself blocks edits, so this does not depend on the model following instructions. It asks you directly.

| While a run is active | `strict` | `warn` |
|---|---|---|
| Edit of an approved file, or outside the project | Allowed | Allowed |
| Edit of another project file | Blocked | You pick: once, add to list, or no |
| Command that deletes files or discards work | You pick: once or no | Same |

- If the lock cannot check a call, or nobody can answer, the call is refused.
- During a run, edit paths must be full and plain. Relative, network, device,
  short (`NAME~1`) and `..` paths are refused.
- A pattern (for linter fixes) names a folder. It stays open until the run ends.
- `/architect-off` turns the lock off. `/clear` and a restart also end the run.
- The default mode is the **Edit lock** setting in `/config`.

**Limits.** This is a guard, not a wall. Shell commands, scripts and other plugins' tools can write files unseen. Only common delete commands are caught. A git worktree made outside the project, and files outside the project such as your user settings, are not locked.

## Without the command

The plugin asks **"Use architect mode?"** with `Yes`, `No` and `Not this session`:

- when you type a new code task (one small model call sorts each typed prompt), and
- before the first project edit, if you were not asked.

After `Yes`, edits wait until the run starts. If the offer fails, or nobody can answer, Claude works as normal. Turn it off with the **Offer architect mode** setting in `/config`.

## Proof that it is on

- A status line shows the mode and the number of approved items.
- `/architect-status` lists approved items and blocked attempts.
- Approval questions and block messages come from the plugin.

## Notes pane

During a run a side pane explains what is happening. It opens on the first note. Reopen it with `/architect-notes`.

| Part | What it shows |
|---|---|
| Decisions | What was chosen, why, and the source |
| Patterns | Ways of working to follow, and the source |
| File tree | An idea of the layout |
| Ask | Type a question. A copy of the chat answers in the pane and the work is not disturbed |

The pane keeps the last 20 decisions, 20 patterns and 5 answers. It is empty after `/clear`. It cannot approve or unlock anything.

**Check the sources.**

- Each note needs an `https` link or a `file:line`. The plugin checks the form, not that the source is true.
- A source link with brackets, `user@host` or non-English letters is refused. Percent-encode those characters.
- A lookalike domain can still pass.
- Answers cannot browse, so their sources are not checked.
- Links come from the model. Only `https` links can be opened. Read the address before you click.
- Each question costs a model call that reads the chat so far.

**Log.** Notes, questions and answers are saved to `<data folder>/projects/<project-key>/notes.md`, next to the backlog. It is plain text and may hold sensitive text from your chat. Delete the file to remove it. The plugin never feeds it back to the model. It stops saving when the file reaches 2 MB, when it is a link or when it cannot be read, and the pane then says so. Two sessions writing for one project at the same moment can lose an entry.

## Experts

| Expert | Covers |
|---|---|
| design | design patterns, SOLID, DRY |
| craft | folder structure, readability, code style, linters |
| security | input, auth, secrets, dependencies |
| database | schema, queries, migrations |
| testing | what to test and how |
| performance | slow paths, resource use |
| accessibility | UI access for all users |
| framework | the framework's own way (Next.js, Fastify, FastAPI and so on) |

### Framework rules

A librarian keeps a short index per framework and major version: one line per rule, with a link. A page is opened only when a decision depends on it. You approve new sources and changed rules before they are saved. Refresh with `/architect-mode:architect refresh <name>`.

## Develop

Run from the repository root:

```
python3 -m unittest discover -s tests
claude plugin test architect-mode
claude plugin validate architect-mode
```

## License

MIT
