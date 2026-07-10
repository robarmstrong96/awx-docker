# Tests

This directory contains fast tests for the AWX image builder wrapper.

The tests keep local checks lightweight. Full image build behavior is covered
by the Dagger build/verify path; unit tests cover small helpers and runtime
contract guardrails.

## Layout

- `unit/`: fast Python tests for wrapper helpers and static runtime guardrails.
