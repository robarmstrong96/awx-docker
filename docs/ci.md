# CI

CI uses Dagger as the command interface.

- `check.yml` runs the fast default `dagger call check --source=.`
- `image-build.yml` runs the transactional image pipeline;
  manual runs can choose the Dagger image name and tag
- The on-demand publication workflow runs the publication gate

Scheduled image builds do not publish images by default.
Image archives and registry pushes are explicit Dagger functions; CI does not
publish unless a later workflow calls `image-publish`.
Strict validation is available with `dagger call strict-check --source=.` when
running advisory checks manually or in a scheduled maintenance workflow.
