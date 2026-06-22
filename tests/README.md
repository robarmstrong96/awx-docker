# Tests

This directory contains fast tests for the AWX image builder wrapper.

The tests focus on behavior that should stay stable without building the full
image on every run: AWX ref resolution, small metadata writers, Make aliases,
and a few Dockerfile invariants.

## Layout

- `unit/`: fast Python tests for wrapper helpers and local command aliases.
- `fixtures/`: fixed example inputs for tests that need sample files.
