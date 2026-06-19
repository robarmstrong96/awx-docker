# Architecture

Dagger is the project command surface and CI orchestration layer.

Python owns policy decisions, GitHub signal normalization, report generation,
public hygiene scanning, and evidence writing.

The Dockerfile assembles the image. Named helpers under `docker/awx/bin` handle
container-specific setup steps.

Shell remains only for small compatibility wrappers and container helper glue.

Evidence is written as canonical JSON for machines and short Markdown for
humans.
