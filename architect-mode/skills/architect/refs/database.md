# database: schema, queries and migrations

- Database constraints protect data (keys, unique, not null, check).
- Types match the data. Money is never a float.
- Indexes exist for real filters and joins.
- No query inside a loop (N+1).
- Reads select only what they need and paginate large results.
- Writes that belong together use one transaction.
- Migrations can be reversed, or state why not.
- Migrations are safe on live data: no long locks, no data loss.
- Destructive changes use expand, migrate, contract steps.
- Connections are pooled and released.
