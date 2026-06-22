# Test Data Fixtures

This directory stores test data used by the test suite.

The directory is named `fixtures` because that is the common testing name for
fixed example inputs. In this project, these files let tests check success,
failure, pending, and missing-signal cases without calling GitHub during the
test run.

The `github/` fixtures model the GitHub status and checks API responses consumed
by upstream-health rule tests.
