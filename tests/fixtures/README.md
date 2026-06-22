# Test Fixtures

This directory stores static inputs used by tests.

Fixtures make upstream-provider and evidence behavior repeatable. They let tests
exercise success, failure, pending, and missing-signal cases without calling
external services during the test run.

The `github/` fixtures model the GitHub status and checks API responses consumed
by upstream-health policy tests.
