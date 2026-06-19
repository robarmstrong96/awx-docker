# CI

CI uses Dagger as the command interface.

- `Project Checks` runs code quality, policy tests, and public readiness jobs
- `Image Pipeline` builds and verifies a moving upstream candidate
- `Production Admission` validates production lock changes and a lock-aware publication gate
- `Production Pipeline` builds and verifies the pinned revision from `awx.lock.yml`
- `Publication Gate` runs the on-demand publication gate

Scheduled image builds do not publish images by default.
Image archives and registry pushes are explicit Dagger functions; CI does not
publish unless a later workflow calls `image-publish`.
Strict validation is available with `dagger call strict-check --source=.` when
running advisory checks manually or in a scheduled maintenance workflow.

Production promotion is lock-file based:

- `promote-candidate` verifies a candidate and writes `awx.lock.yml`
- `production-admission` checks the lock, promotion evidence, public readiness, and publication gate
- `production-pipeline` builds and verifies the pinned revision from the lock

Evidence uploads are required. If an evidence artifact cannot be uploaded, the
workflow should fail instead of silently passing.
