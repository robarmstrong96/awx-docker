# AWX Docker Proof-of-Concept Image Builder

This repository builds an unofficial proof-of-concept AWX container image for
local testing and CI experimentation.

It is not affiliated with, endorsed by, or supported by Red Hat, Ansible, or the
AWX project. It is not intended for production use.

For normal AWX installation and lifecycle management, use the AWX Operator.

## Basic Use

We utilize Dagger for building and testing the image. Install Dagger from https://dagger.io.

```bash
dagger call check --source=.
dagger call upstream-health --source=. --upstream-ref=devel
dagger call image-build --source=. --awx-ref=devel --image-name=awx-devel --image-tag=devel
dagger call image-verify --source=. --awx-ref=devel --image-name=awx-devel --image-tag=devel
dagger call publication-gate --source=. --upstream-ref=devel
```

## Optional Make aliases

These commands are provided for convenience.

```bash
make check
make strict-check
make build
make verify-image
make upstream-health
make public-readiness
make publication-gate
```

## Defaults

Example defaults for the build:

- AWX repo: `https://github.com/ansible/awx.git`
- AWX ref: `devel`
- Upstream health provider: `auto`
- Image tag: `awx-devel:devel`
- Dockerfile: `docker/awx/Dockerfile`

The build clones upstream AWX during the Docker image build. This repository
does not vendor the AWX source tree.

## Notices

Wrapper files in this repository are licensed under Apache-2.0. Built images
include upstream AWX source and retain upstream license and source revision
metadata under `/usr/share/licenses/awx-wrapper/`.
