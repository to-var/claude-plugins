# framework: the detected framework's own way

- Use the framework's own way before a custom one.
- Judge against the installed major version, never another one.
- Files and folders follow the framework's conventions.
- Use built-in features (routing, data loading, validation, errors, config) before new code or dependencies.
- No deprecated or removed APIs.
- Respect server and client boundaries where the framework has them.
- Middleware, plugins and hooks follow the framework's order and lifetime rules.
- Read only the index rules whose "read when" topic matches the task.
- Open a rule's link only when a proposal depends on that rule.
- Mark each rule you use `verified` (you read the page now) or `from index`.
- When a page disagrees with a rule, the page wins. Report the corrected line.
