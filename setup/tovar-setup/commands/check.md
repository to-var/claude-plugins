---
description: "Show what /tovar-setup:apply would change on this machine, without changing anything"
---

Run these commands and read their JSON output; you do not need to show the
raw JSON to the user:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" plan-plugins
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" plan-settings
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" plan-statusline
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" plan-claude-md
```

For each one, tell the user in plain words:
- `"empty"`: nothing was captured for this group, skip it.
- `"match"`: this machine already has it.
- `"differs"`: list what would change (new marketplaces, new plugins,
  changed settings, or that the CLAUDE.md block is missing or out of date).

Do not run any `apply-*` command. This is a read-only check.
