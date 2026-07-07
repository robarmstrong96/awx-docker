# Tests

This directory contains fast tests for the AWX image builder wrapper.

The tests keep local checks lightweight. Full image build behavior is covered
by the Dagger build/verify path; unit tests cover small helpers and the
lint/build Just recipes.

## Layout

- `unit/`: fast Python tests for wrapper helpers and local recipe wiring.
