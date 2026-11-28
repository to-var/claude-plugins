# Agent rules

## Versioning and releases

Every plugin has its own version in `<plugin>/.claude-plugin/plugin.json`. Claude Code only updates an installed plugin when that version changes, so a change that ships without a bump never reaches the user.

When a change touches a plugin's behaviour (anything under `tovar-core/`, `tovar-mods/`, `tovar-shell/` or `architect-mode/` other than tests and docs), do this in the same branch, without being asked:

1. **Bump that plugin's version** in its `plugin.json`. Bump only the plugins you changed.
   - `fix:` is a patch (1.0.0 to 1.0.1).
   - `feat:` is a minor (a new skill, skin, bar, option or command): 1.0.0 to 1.1.0.
   - A breaking change is a major (a renamed or removed command or setting, a changed data format): 1.0.0 to 2.0.0.
2. **Add the entry to `CHANGELOG.md`** under a new `## <plugin> <version> (<YYYY-MM-DD>)` heading, above that plugin's older entries. Use `### Added`, `### Changed` and `### Fixed`, in plain words for the user.
3. **Commit both together** as `chore: release <plugin> <version>`, after the change they describe. Follow the commit rules in `CLAUDE.md`.

Changes to tests, README, `CLAUDE.md` or `AGENTS.md` only do not bump anything.

After the PR is merged into `main`, offer to tag the merge commit `<plugin>-v<version>` (for example `tovar-shell-v1.1.0`) and push the tag to `origin`. Pushing is outward-facing, so ask first. Then remind the user to run `claude plugin marketplace update tovar` and `claude plugin update <plugin>@tovar`.

The marketplace itself (`.claude-plugin/marketplace.json`) has no version. `tests/test_tovar_release.py` fails when a plugin's version has no matching `CHANGELOG.md` entry.
