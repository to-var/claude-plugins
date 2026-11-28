# Framework rules

Follow the framework's own way. Keep short rules with links, never a copy of the docs.

## Index

`SKILL.md` names `<data folder>`.

One file per framework and major version: `<data folder>/frameworks/<name>@<major>.md`. Take the version from the project manifests. Replace `/` in a package name with `-`.

```
source: <official site>
checked: <date>

- <one short rule>
  -> <link> (read when: <topic>)
```

## Use

1. For each framework the task touches, look for its index file.
2. Offer the `framework` expert in the experts question.
3. If the file is missing, or lacks a topic the task needs, start the agent `architect-mode:librarian` with the framework, major version, topics, today's date and the current file.
4. Show the user the new sources and the added or changed rules. Save the file only after a yes.
5. Start `architect-mode:framework` with the index file paths and the reference path.
6. In proposals, mark each rule `verified` or `from index`.

## Refresh

Refresh a file when: the major version is new, a link is dead, a page disagrees with a rule (the page wins), or the user asks with `/architect-mode:architect refresh <name>`. Show the changes and save only after a yes. There is no schedule.

If no source can be reached, say so and continue without that rule.
