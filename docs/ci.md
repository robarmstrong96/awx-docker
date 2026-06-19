# CI

CI uses Dagger as the command interface.

- `check.yml` runs `dagger call check --source=.` and then verifies the
  optional Make aliases with `make check` and `make upstream-health`
- `image-build.yml` checks upstream health, builds the image, and verifies it;
  manual runs can choose the Dagger image name and tag
- The on-demand publication workflow runs the publication gate

Scheduled image builds do not publish images by default.
