# performance: slow paths and resource use

- Name the measured or expected hot path before you optimize.
- Watch for work that grows with data size (nested loops, N+1).
- Independent I/O runs in parallel.
- Large data is streamed or paginated.
- Each cache has a clear key, lifetime and invalidation.
- No blocking work on request or UI threads.
- Timers, listeners and connections are released.
- Client code ships only what the page needs.
- Do not trade readability for speed without a reason.
