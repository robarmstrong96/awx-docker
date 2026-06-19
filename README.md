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
dagger call upstream-health --source=. --upstream-ref=devel --provider=auto
dagger call image-pipeline --source=. --upstream-ref=devel --provider=auto --image-name=awx-devel --image-tag=devel export --path=build/evidence
dagger call image-export --source=. --upstream-ref=devel --image-ref=awx-devel:devel export --path=build/out/awx-devel.tar
dagger call publication-gate --source=. --upstream-ref=devel
dagger call promote-candidate --source=. --upstream-ref=devel
dagger call production-admission --source=. export --path=build/evidence
dagger call production-pipeline --source=. export --path=build/evidence
```

## Optional Make aliases

These commands are provided for convenience.

```bash
make check
make strict-check
make build
make upstream-health
make public-readiness
make publication-gate
make production-admission
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

Production-style builds use `awx.lock.yml`. That file pins the exact upstream
AWX revision; production commands build from the pinned SHA instead of the
floating branch name.

See `docs/production-branch.md` for the protected production branch model.

## Notices

Wrapper files in this repository are licensed under Apache-2.0. Built images
include upstream AWX source and retain upstream license and source revision
metadata under `/usr/share/licenses/awx-wrapper/`.
