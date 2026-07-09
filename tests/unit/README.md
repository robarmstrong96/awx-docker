# Unit Tests

This directory contains fast unit tests for the wrapper code.

These tests avoid full image builds. They cover the wrapper contracts that are
cheap to check locally: ref resolution, runtime startup ordering, UI source
pinning, AWX UI bundle wiring, starter EE pins, and AWX Python constraint
rendering.
