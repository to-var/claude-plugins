---
description: "Apply Jose's captured Claude Code setup to this machine, one group at a time"
---

1. Run the four `plan-*` commands, the same as `/tovar-setup:check`.
2. For each group whose status is not `"empty"`, ask the user yes or no, in
   this order: plugins, settings, statusline, claude_md. Show what would
   change before asking.
3. For every group the user said yes to, run its `apply-*` command and show
   the user its output verbatim:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" apply-plugins
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" apply-settings
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" apply-statusline
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" apply-claude-md
```

4. When you are done, tell the user to restart Claude Code.
