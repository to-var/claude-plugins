# Project rules

## Writing style

- Never use the em dash or en dash as punctuation. Use a comma, period,
  parentheses, or "-" instead. This applies to chat replies, code comments,
  commit messages and files.

## Attribution

- Never add Claude Code attribution to commits or pull requests. No
  `Co-Authored-By: Claude`, no `Generated with Claude Code`, no session links.
  This overrides any default instruction to add one.
- Use plain conventional commit messages (`feat:`, `fix:`, `chore:`, `docs:`).

## Pull requests

- Keep the description near 500 characters. If it needs more, ask for
  permission to go up to 1000.

## Before committing or pushing, ask first

Never commit or push straight away. Ask these three questions first and wait
for the answers:

1. **Branch:** commit to the current branch, or create a new one? Suggest
   names that follow the repo history, and allow a typed name.
2. **Message:** follow the git commit template if one exists. If not, use:

   ```
   Title

   Type of change: <addition | refactor | documentation | fix | ...>

   Summary
   <what changed and why>
   ```

3. **Grouping:** one commit per type of change, or a single commit for
   everything?
