# AWX Docker Proof-of-Concept Image Builder

This repository builds an unofficial proof-of-concept AWX container image for
local testing and CI experimentation.

It is not affiliated with, endorsed by, or supported by Red Hat, Ansible, or the
AWX project. It is not intended for production use.

For normal AWX installation and lifecycle management, use the AWX Operator.

## Tools Used

- Dagger: primary command surface for local checks, image builds, verification,
  and CI workflows.
- Docker/BuildKit: builds the multi-stage AWX image and enables build features
  such as SSH mounts for private dependency access.
- Python: implements rule checks, evidence generation, upstream-health
  evaluation, and production lock handling.
- Make: optional local aliases for common Dagger commands.

## Basic Use

We utilize Dagger for building and testing the image. Install Dagger from https://dagger.io.

```bash
# Run the fast project checks.
dagger call check --source=.

# Check whether the selected upstream AWX ref is healthy enough to use.
dagger call upstream-health --source=. --upstream-repository=https://github.com/ansible/awx.git --upstream-ref=devel --provider=auto

# Resolve, build, verify, and write image evidence.
dagger call image-pipeline --source=. --upstream-ref=devel export --path=build/evidence

# Build, verify, gate, publish, and write publication evidence.
dagger call image-publish --source=. --upstream-ref=devel --image-ref=ghcr.io/example/awx-devel:development export --path=build/evidence

# Scan the repository for public-readiness issues.
dagger call public-readiness --source=. export --path=build/evidence

# Run the gate required before public repository or image publication.
dagger call publication-gate --source=. export --path=build/evidence

# Export a verified image as an OCI tarball.
dagger call image-export --source=. --upstream-ref=devel --image-ref=awx-devel:development export --path=build/out/awx-devel.tar

# Verify a candidate and write an updated production lock.
dagger call promote-candidate --source=. --upstream-ref=devel

# Validate a production branch change before merge.
dagger call production-admission --source=. export --path=build/evidence

# Build, verify, gate, and publish the locked production image.
dagger call production-publish --source=. export --path=build/evidence
```

## Optional Make aliases

The [Makefile](Makefile) is only a convenience layer. Dagger remains the
canonical command surface for build, test, verification, and publication
workflows.

```bash
make check
make strict-check
make build
make upstream-health
make public-readiness
make publication-gate
make production-admission
make production-publish
```

## Defaults

Example defaults for the build:

- Upstream AWX repo: `https://github.com/ansible/awx.git`
- Upstream AWX ref: `devel`
- Upstream health provider: `auto`
- Development image tag: `awx-devel:development`
- Production image tags: `awx-devel:production`, `awx-devel:latest`
- Dockerfile: `docker/awx/Dockerfile`

The build clones upstream AWX during the Docker image build. This repository
does not store a copy of the AWX source tree.

## Branch Model

`development` follows moving upstream AWX refs for integration and testing.

`production` builds only from `awx.lock.yml` pinned revisions and accepts
changes through protected pull requests.

Production-style builds use `awx.lock.yml`. That file pins the exact upstream
AWX revision; production commands build from the pinned SHA instead of the
floating branch name.

## Notices

Wrapper files in this repository are licensed under Apache-2.0. Built images
include upstream AWX source and retain upstream license and source revision
metadata under `/usr/share/licenses/awx-wrapper/`.
