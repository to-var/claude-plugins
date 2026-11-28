# design: design patterns, SOLID and DRY

- A pattern solves a problem that exists now. No pattern "for later".
- Single responsibility: each unit has one reason to change.
- Open/closed: add behavior without editing many callers.
- Substitution: subtypes keep the promises of the base type.
- Interface segregation: callers depend only on what they use.
- Dependency inversion: business rules do not import infrastructure details.
- DRY: one source of truth for each rule. Similar code with different reasons to change may stay apart.
- YAGNI: no code without a current need.
- Prefer composition over inheritance.
- Side effects sit at the edges. Core logic is testable without them.
- Each failure has one clear owner that handles it.
- A new abstraction has at least two real users, or a stated reason.
