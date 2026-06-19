# CI

CI uses Dagger as the command interface.

- `check.yml` runs the fast default `dagger call check --source=.`
- `image-build.yml` checks upstream health, builds the image, and verifies it;
  manual runs can choose the Dagger image name and tag
- The on-demand publication workflow runs the publication gate

Scheduled image builds do not publish images by default.
Strict validation is available with `dagger call strict-check --source=.` when
running advisory checks manually or in a scheduled maintenance workflow.
