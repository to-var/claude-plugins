---
description: "Ask Jose what to publish from this machine's setup into setup.json"
---

Run this only inside the claude-plugins repo, on Jose's own machine.

1. **CLAUDE.md.** Run:

   ```
   python3 setup/tovar-setup/scripts/setup.py read-md
   ```

   For each section in its `sections` list, ask Jose two questions: include
   it, and if so, word for word, shortened, or generalized (no names, paths
   or emails). Build the approved Markdown from the sections he said yes to,
   in their original order, each as a `## heading` with its text. Show him
   the final text and wait for "publish" before saving it:

   ```
   python3 setup/tovar-setup/scripts/setup.py save-md
   ```

   sending `{"text": "<approved markdown>"}` as JSON on its stdin.

2. **Plugins, settings, status line.** Run:

   ```
   python3 setup/tovar-setup/scripts/setup.py read-state
   ```

   Ask Jose, per item, whether to include it:
   - Each marketplace name in `marketplaces` (its value has `source.repo`).
   - Each plugin key in `plugins`.
   - Each key in `settings`.
   - The `statusline` value, as one item (include it or not).

   Never offer hooks or credentials; `read-state` does not include them.

   Important: `read-state` returns `marketplaces` as a dict keyed by name,
   but `save-state` expects a list. For each marketplace Jose approves,
   build `{"name": <the key>, "repo": <its value>.source.repo}` - do not
   pass `read-state`'s `marketplaces` dict through unchanged; it is shaped
   differently from what `save-state` expects.

   Build the approved JSON in this shape, then send it as stdin to
   `save-state`:

   ```json
   {
     "marketplaces": [{"name": "tovar", "repo": "to-var/claude-plugins"}],
     "plugins": ["tovar-themes-pop@tovar"],
     "settings": {"model": "sonnet"},
     "statusline": {"type": "command", "command": "..."}
   }
   ```

   ```
   python3 setup/tovar-setup/scripts/setup.py save-state
   ```

3. Tell Jose `setup/tovar-setup/setup.json` changed and to review the diff
   before committing.
