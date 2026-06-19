# CI

CI uses Dagger as the command interface.

- `check.yml` runs `dagger call check --source=.` and then verifies the
  Makefile compatibility shims with `make check` and `make upstream-health`
- `image-build.yml` checks upstream health, builds the image, and verifies it;
  manual runs can choose the Dagger image name and tag
- `release-check.yml` runs publication readiness checks on demand

Scheduled image builds do not publish images by default.
