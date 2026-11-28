# security: input, authentication, secrets and dependencies

- Validate and bound all input at trust boundaries.
- Use parameterized queries. No string-built SQL, shell or HTML.
- Encode output for the place where it lands.
- Check authentication on the server.
- Check authorization per object, not only per route.
- No secrets in code, logs, client bundles or git history.
- Do not log or return sensitive data without need.
- File paths from users cannot leave their folder.
- Restrict outgoing requests to user-given URLs (SSRF).
- Cookies and sessions use safe flags and expiry.
- New dependencies are needed, maintained and locked.
- Errors do not show internals to users.
- Rate limits exist where abuse costs money or access.
