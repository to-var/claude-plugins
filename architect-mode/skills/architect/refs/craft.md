# craft: folder structure, readability, code style and linters

- Follow the project's existing layout unless the task is to change it.
- Group files by feature or responsibility, as the framework expects.
- One clear purpose per file and folder. Names say what is inside.
- Names reveal intent. No unexplained short names.
- Functions are small enough to read at once.
- Early returns over deep nesting.
- Comments explain why, not what.
- No dead code, commented-out code or unused exports.
- The project linter and formatter pass. Their config is the style authority.
- No linter rule is disabled without a written reason.
- Public interfaces are typed where the language allows it.
- A move or rename updates every import and reference.
