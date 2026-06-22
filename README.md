# AWX Docker Proof-of-Concept Image Builder

This repository builds an unofficial AWX container image for local testing and
CI experimentation.

It is not affiliated with, endorsed by, or supported by Red Hat, Ansible, or the
AWX project. It is not intended for production use. For normal AWX installation
and lifecycle management, use the AWX Operator.

## What This Is

This is a thin image builder. The Dockerfile clones upstream AWX during the
image build, assembles the runtime files, and keeps source and license metadata
inside the image.

Dagger is the main command surface. Make is only a small convenience layer for
common local commands.

## Requirements

- Docker or another BuildKit-capable container builder
- Dagger
- Python and uv for local tests outside Dagger

## Build And Verify

```bash
# Run formatting, lint, shell, workflow, and unit checks.
dagger call check --source=.

# Resolve an AWX branch, tag, or commit to a concrete SHA.
dagger call resolve-ref --source=. --upstream-ref=devel

# Build the image.
dagger call build --source=. --upstream-ref=devel

# Build the image and run the runtime contract check.
dagger call verify --source=. --upstream-ref=devel export --path=build/evidence

# Export a verified image as an OCI tarball.
dagger call export --source=. --upstream-ref=devel --image-ref=awx-devel:devel export --path=build/out/awx-devel.tar
```

## Publish image with CI/CD

The `Publish` workflow builds, verifies, and pushes an image from GitHub
Actions. It publishes to `ghcr.io/<owner>/<repo>:<tag>` by default when
`image_ref` is not set.

Optional Make aliases:

```bash
make check
make lint
make format
make test
make build
make verify
make export
make clean
make distclean
```

## Defaults

- Upstream AWX repo: `https://github.com/ansible/awx.git`
- Upstream AWX ref: `devel`
- Receptor image: `quay.io/ansible/receptor:devel`
- Local image tag: `awx-devel:devel`
- Dockerfile: `docker/awx/Dockerfile`

Useful environment variables for Make aliases:

- `UPSTREAM_REF`: AWX branch, tag, or commit to build
- `IMAGE_NAME`: local image name used by `make build` and `make verify`
- `IMAGE_TAG`: local image tag used by `make build` and `make verify`
- `IMAGE_REF`: image reference used by `make export`
- `OUTPUT`: tarball path used by `make export`

## Runtime Check

`verify` runs `docker/awx/bin/verify-runtime-contract` inside the built image.
That check confirms the copied AWX source, wrapper entrypoint, supervisor
configuration, `awx-manage`, source revision files, and license files are
present.

## Notices

Wrapper files in this repository are licensed under Apache-2.0. Built images
include upstream AWX source and retain upstream license and source revision
metadata under `/usr/share/licenses/awx-wrapper/`.
