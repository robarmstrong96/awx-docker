# Tests

This directory contains the project test suite.

The tests focus on the wrapper behavior that must stay stable around Dagger
commands, rule decisions, evidence formats, workflow contracts, and production
lock handling. They are meant to catch regressions in repository behavior
without requiring a live AWX checkout or a running image build for every check.

## Layout

- `unit/`: fast tests for Python helpers, CLI behavior, rule logic, schemas,
  workflow definitions, and Make aliases.
- `fixtures/`: test data files. They give tests fixed examples to read, such as
  mocked GitHub responses, instead of calling external services.
