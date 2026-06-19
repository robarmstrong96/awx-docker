# CI

CI uses Dagger as the command interface.

- `Project Checks` runs code quality, policy tests, and public readiness jobs
- `Image Pipeline` builds, verifies, gates, and publishes a moving upstream candidate
- `Production Admission` validates production lock changes and a lock-aware publication gate
- `Production Pipeline` builds, verifies, gates, and publishes the pinned revision from `awx.lock.yml`
- `Publication Gate` runs the on-demand publication gate

The image workflow publishes `ghcr.io/<owner>/awx-devel:development` on
development pushes, on schedule, and on manual dispatch by default. The
production workflow publishes the locked image as both `production` and
`latest`.
Strict validation is available with `dagger call strict-check --source=.` when
running advisory checks manually or in a scheduled maintenance workflow.

Production promotion is lock-file based:

- `promote-candidate` verifies a candidate and writes `awx.lock.yml`
- `production-admission` checks the lock, promotion evidence, public readiness, and publication gate
- `production-publish` builds, verifies, gates, and publishes the pinned revision from the lock

Evidence uploads are required. If an evidence artifact cannot be uploaded, the
workflow should fail instead of silently passing.
