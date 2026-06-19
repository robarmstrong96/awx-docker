# CI

CI uses Dagger as the command interface.

- `check.yml` runs `dagger call check --source=.`
- `image-build.yml` checks upstream health, builds the image, and verifies it
- `release-check.yml` runs publication readiness checks on demand

Scheduled image builds do not publish images by default.
