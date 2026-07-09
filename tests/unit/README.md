# Unit Tests

This directory contains fast unit tests for the wrapper code.

These tests avoid full image builds. They cover the wrapper contracts that are
cheap to check locally: ref resolution, metadata writers, runtime startup
ordering, UI source pinning, and AWX Python constraint rendering.
