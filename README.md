# AWX Docker Proof-of-Concept Image Builder

This repository builds an unofficial AWX container image for local testing and
CI experimentation.

It is not affiliated with, endorsed by, or supported by Red Hat, Ansible, or the
AWX project. It is not intended for production use. For normal AWX installation
and lifecycle management, use the AWX Operator.

## What This Is

This is a thin image builder for trying AWX locally. It has three buildable
deliverables:

- `docker/awx` builds the AWX control-plane image.
- `docker/awx-ui` builds a static UI bundle that can be mounted into AWX.
- `docker/awx-ee` builds a starter execution environment image for jobs.

Dagger is the main command surface. Just is only a small convenience layer for
common local commands. Tool files that are discovered by convention, such as
`dagger.json`, `pyproject.toml`, `uv.lock`, and `.dockerignore`, stay at the
repo root so the normal commands keep working.

## Component Versions

The default versions live in `config/components/components.toml`: AWX, AWX UI,
the AWX UI bundle tag, the starter EE image tag, the AWX UI delivery mode, the
base images, receptor, the local image tag, the platform, and the small
dependency files this wrapper owns. It also pins the Python/uv image Dagger
uses for local checks so the test environment is visible in the same place as
the build inputs.

Dagger reads that file through the Python config layer and passes the values to
the Dockerfile as build arguments. The Dockerfile still has matching `ARG`
defaults so a plain `docker build` has a reasonable fallback. It cannot read
the component manifest itself before `ARG` and `FROM` are evaluated.

Use `docker/awx/constraints/awx-python.yaml` for intentional AWX control-plane
Python overrides. Upstream AWX requirements are still the baseline. Pins in
this file narrow that resolution, and the build fails if a pin cannot work with
the upstream requirements.

Job Ansible and collection versions are controlled by the execution environment
image selected by AWX job templates, not by the AWX web/task image. The starter
EE in `docker/awx-ee` pins `ansible-core` and `ansible-runner` in
`execution-environment.yml`, lists collections in `requirements.yml`, and keeps
extra Python and RPM dependencies in `requirements.txt` and `bindep.txt`.

## Requirements

- Docker or another BuildKit-capable container builder
- Dagger
- Just for local command aliases
- uv with Python 3.12 for local tests outside Dagger

## Build And Verify

```bash
# Run formatting, lint, shell, and unit checks.
dagger call check --source=.

# Resolve an AWX branch, tag, or commit to a concrete SHA.
dagger call resolve-ref --source=. --upstream-ref=devel

# Build the image.
dagger call build --source=. --upstream-ref=devel --awx-ui-ref=v2.4.313

# Build only the sideloadable AWX UI bundle.
dagger call build-ui --source=. --awx-ui-ref=v2.4.313

# Build the starter execution environment image.
dagger call build-ee --source=.

# Build the image and run the runtime contract check.
dagger call verify --source=. --upstream-ref=devel --awx-ui-ref=v2.4.313

# Export a verified image as an OCI tarball.
dagger call export --source=. --upstream-ref=devel --awx-ui-ref=v2.4.313 --image-ref=awx-devel:devel export --path=build/out/awx-devel.tar

# Export the UI bundle as a directory.
dagger call export-ui --source=. export --path=build/out/awx-ui-static

# Export the starter EE image as an OCI tarball.
dagger call export-ee --source=. --image-ref=awx-ee:devel export --path=build/out/awx-ee.tar
```

The AWX UI source is pinned separately from the AWX server source. The default
lives in `config/components/components.toml`, and `--awx-ui-ref` can still
override it for one Dagger call. Upstream AWX normally clones `ansible-ui` from
`main` while building UI assets; this wrapper checks out the configured UI ref
first so `make ui` builds from a known tag or commit instead of a moving branch.

## AWX UI Delivery

The default `embedded` mode builds the pinned AWX UI into the image. Use
`sideloaded` when you want one AWX runtime image and a separately built UI
bundle:

```bash
dagger call export \
  --source=. \
  --awx-ui-delivery=sideloaded \
  --image-ref=awx-devel:sideloaded \
  export --path=build/out/awx-devel-sideloaded.tar
```

Build the bundle with `dagger call export-ui --source=. export
--path=build/out/awx-ui-static`, then mount that directory at
`/var/lib/awx/public/static`. That directory is what nginx serves for
`/static`, `/locales`, and `/favicon.ico`. The image does not copy or sync
sideloaded assets during startup.

## Execution Environment

`docker/awx-ee/execution-environment.yml` is a minimal Ansible Builder v3
definition. It uses an Ansible Runner base image, pins `ansible-core==2.15.13`
and `ansible-runner==2.4.0`, and installs the starter collections listed in
`docker/awx-ee/requirements.yml`.

```bash
dagger call build-ee --source=.
dagger call export-ee --source=. --image-ref=awx-ee:devel export --path=build/out/awx-ee.tar
```

Use this image from AWX job templates or replace it with your own EE image when
playbooks need different core, runner, collection, Python, or RPM dependencies.

## Example Compose Smoke Test

`config/examples/compose/compose.example.yaml` starts this image with local
Postgres and Redis containers. It is intended for a quick smoke test of a
published or locally built image, not as a supported production deployment.

```bash
cp config/examples/compose/.env.example config/examples/compose/.env
# Edit .env and replace every change-me value before starting the stack.
docker compose \
  --env-file config/examples/compose/.env \
  -f config/examples/compose/compose.example.yaml \
  up -d
```

The example defaults to `ghcr.io/robarmstrong96/awx-docker:production`. To test a
local export or another registry tag, set `AWX_IMAGE` in `.env`.

## Example Podman Pod Smoke Test

`config/examples/podman/pod.example.yaml` starts the same basic smoke-test
stack through `podman kube play`: one pod with Postgres, Redis, and the AWX
container. It uses loopback addresses between containers because containers in a
pod share one network namespace.

Edit the `change-me` values in the file before use. The example publishes AWX
on `http://localhost:8014` so it can run next to the Compose example, which
defaults to port `8013`.

```bash
podman kube play --replace config/examples/podman/pod.example.yaml
podman pod logs -f awx-docker-example
podman kube play --down config/examples/podman/pod.example.yaml --force
```

The AWX container is privileged because it starts nested Podman containers for
execution environments. Rootless Podman works when the host allows privileged
rootless containers; otherwise use rootful Podman for this smoke test. Deeply
nested development setups, such as Podman inside Podman inside Docker, may need
local storage or cgroup overrides that normal host Podman runs should not need.

Example browser snapshots from this pod:

- [Login screen](docs/snapshots/awx-pod-login.png)
- [Overview dashboard](docs/snapshots/awx-pod-dashboard.png)
- [Jobs list](docs/snapshots/awx-pod-jobs.png)

## Publish image with CI/CD

The `Publish` workflow builds, verifies, and pushes an image from GitHub
Actions. It publishes to `ghcr.io/<owner>/<repo>:<tag>` by default when
`image_ref` is not set.

Optional Just recipes provide short aliases for the default Dagger calls and
local cleanup:

```bash
just check
just lint
just format
just test
just build
just build-ui
just build-ee
just verify
just export
just export-ui
just export-ee
just clean
just distclean
```

Use Dagger directly when overriding build inputs:

```bash
dagger call build --source=. --upstream-ref=devel --awx-ui-ref=v2.4.313
dagger call export --source=. --image-ref=awx-devel:devel export --path=build/out/awx-devel.tar
dagger call export-ui --source=. --awx-ui-ref=v2.4.313 export --path=build/out/awx-ui-static
dagger call export-ee --source=. --image-ref=awx-ee:devel export --path=build/out/awx-ee.tar
```

## Defaults

- Component manifest: `config/components/components.toml`
- Upstream AWX repo: `https://github.com/ansible/awx.git`
- Upstream AWX ref: `devel`
- Upstream AWX UI repo: `https://github.com/ansible/ansible-ui.git`
- Upstream AWX UI ref: `v2.4.313`
- AWX UI delivery: `embedded`
- AWX UI bundle export path: `build/out/awx-ui-static`
- Base image: `quay.io/centos/centos:stream9`
- EE base image: `quay.io/ansible/ansible-runner:stable-2.15-devel`
- EE local image tag: `awx-ee:devel`
- EE Ansible core: `ansible-core==2.15.13`
- EE Ansible Runner: `ansible-runner==2.4.0`
- Receptor image: `quay.io/ansible/receptor:devel`
- AWX Python constraints: `docker/awx/constraints/awx-python.yaml`
- Dagger check Python: `3.12`
- Dagger check image: `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`
- Local image tag: `awx-devel:devel`
- AWX Dockerfile: `docker/awx/Dockerfile`
- AWX UI Dockerfile: `docker/awx-ui/Dockerfile`
- AWX EE definition: `docker/awx-ee/execution-environment.yml`

## Runtime Check

`verify` runs `docker/awx/bin/verify-runtime-contract` inside the built image.
That check confirms the copied AWX source, wrapper entrypoint, supervisor
configuration, `awx-manage`, source revision files, and license files are
present.

## Notices

Wrapper files in this repository are licensed under Apache-2.0. Built images
include upstream AWX source and retain upstream license and source revision
metadata under `/usr/share/licenses/awx-wrapper/`.
