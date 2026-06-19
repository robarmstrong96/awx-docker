# Architecture

Dagger is the project command surface and CI orchestration layer.

Python owns policy decisions, upstream provider normalization, report generation,
public readiness checks, and evidence writing.

The Dockerfile assembles the image. Named helpers under `docker/awx/bin` handle
container-specific setup steps.

Shell remains only for runtime scripts and container helper glue.

Evidence is written as canonical JSON for machines and short Markdown for
humans.

Production promotion is lock-file based. `production` builds from
`awx.lock.yml` pinned revisions instead of rediscovering floating upstream refs.
