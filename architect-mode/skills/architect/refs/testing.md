# testing: what to test and how

- Test behavior, not private details.
- Each new behavior has a test that failed before the code.
- Cover failure paths and limits, not only the happy path.
- A bug fix starts with a test that reproduces it.
- Mock only slow or external parts.
- Tests are independent and give the same result each run.
- Test names state the expected behavior.
- A refactor has a passing baseline before the first change.
- Follow the project's existing test tool and layout.
