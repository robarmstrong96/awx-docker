# Unit Tests

This directory contains fast unit tests for repository behavior.

The tests cover policy classification, evidence schemas, production lock
validation, CLI wiring, workflow expectations, Make aliases, and other local
contracts. They should stay lightweight and deterministic so they can run in
local development and CI before slower image or Dagger workflows.
