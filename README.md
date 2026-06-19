# AWX Docker Proof-of-Concept Image Builder

This repository builds an unofficial proof-of-concept AWX container image for
local testing and CI experimentation.

It is not affiliated with, endorsed by, or supported by Red Hat, Ansible, or the
AWX project. It is not intended for production use.

For normal AWX installation and lifecycle management, use the AWX Operator.

## Basic Use

```bash
dagger call check --source=.
dagger call upstream-health --source=. --awx-ref=devel
dagger call image-build --source=. --awx-ref=devel --image-name=awx-devel --image-tag=devel
dagger call image-verify --source=. --awx-ref=devel --image-name=awx-devel --image-tag=devel
dagger call release-check --source=. --awx-ref=devel
```

Compatibility shims:

```bash
make check
make build
make verify-image
make upstream-health
make release-check
```

## Defaults

- AWX repo: `https://github.com/ansible/awx.git`
- AWX ref: `devel`
- Image tag: `awx-devel:devel`
- Dockerfile: `docker/awx/Dockerfile`

The build clones upstream AWX during the Docker image build. This repository
does not vendor the AWX source tree.

## Notices

Wrapper files in this repository are licensed under Apache-2.0. Built images
include upstream AWX source and retain upstream license and source revision
metadata under `/usr/share/licenses/awx-wrapper/`.
