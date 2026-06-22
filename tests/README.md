# Tests

This directory contains the project test suite.

The tests focus on the wrapper behavior that must stay stable around Dagger
commands, policy decisions, evidence formats, workflow contracts, and production
lock handling. They are meant to catch regressions in repository behavior
without requiring a live AWX checkout or a running image build for every check.

## Layout

- `unit/`: fast tests for Python helpers, CLI behavior, policy logic, schemas,
  workflow definitions, and Make aliases.
- `fixtures/`: small static inputs used by tests, especially mocked upstream
  provider responses.
