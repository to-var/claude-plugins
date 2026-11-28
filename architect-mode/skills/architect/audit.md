# Audit

For projects that existed before this tool. An audit changes no code.

1. Map the project: stack, folders, tests, linter.
2. Ask which experts run: all, some, or one area.
3. Call `mcp__architect-mode__start`. Do not call `mcp__architect-mode__plan` for code until the user picks an item.
4. Start the experts. On a big project, give them one area or folder at a time. A `block` does not stop the scan.
5. Write the backlog. `block` items go to the top.
6. Ask the user to pick an item. Run it as a refactor (`refactor.md`), then set its status. With no pick, call `mcp__architect-mode__finish`.

## Backlog

| # | Area | Finding | Verdict | Risk to fix | Status |
|---|---|---|---|---|---|

- Status is `open`, `done` or `skipped` with the user's reason.
- Read the old backlog first. Do not bring a `skipped` item back. Keep item numbers.
- Default order: security, tests, linter and format, folders, best practices.
- Cite `file:line` in each finding. Never copy a secret into the backlog.

## Where it lives

`SKILL.md` names `<data folder>`. Default: `<data folder>/projects/<project-key>/backlog.md`. `<project-key>` is the project root path with every run of other characters than letters and numbers turned into `-`.

A project can set another place in its own instructions, for example its `CLAUDE.md`. Then:

- Before you save security items inside the project, warn that git may publish them.
- Before you write it, send one `mcp__architect-mode__plan` call that holds only the backlog file, or the lock blocks it.
