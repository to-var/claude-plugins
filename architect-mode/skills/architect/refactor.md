# Refactor

New code shape, same behavior. Follow these steps in place of the build workflow.

1. Get the problem in the user's words. Examples: folder structure, best practices, linters, readability, security, testing.
2. Map who uses the affected code.
3. Call `mcp__architect-mode__start`. If a run is already active (from an audit), keep it.
4. Decide first, then ask which experts run (workflow steps 4 to 6). They judge: is it worth it, which way, what risk. Then start the planner (steps 7 and 8).
5. Run the tests as a baseline. With no tests, offer to write them first: send the test files with `mcp__architect-mode__plan`, then write them. If the user says no, mark the work `unverified` and say so in every report.
6. Propose small steps. Send the change list for the first steps with `mcp__architect-mode__plan`.
7. The builder does one step. Run the tests. Repeat. A failed test stops the run: show it and ask the user.
8. The same experts check: same behavior, problem gone.
9. Report, then call `mcp__architect-mode__finish`.

Rules:

- The change list uses `move` and `rename` as well as `add`, `change` and `delete`. Move a file only after its item is approved. Update every import and reference.
- A `delete` needs proof that nothing uses the code. Show the search you ran.
- A security fix changes behavior on purpose. State each such change in the change list.
- Linter or formatter auto-fix is its own step with no logic changes. Send a folder pattern plus the command in `patterns`, not every file.
- A step that needs an unlisted file needs a new plan call.
