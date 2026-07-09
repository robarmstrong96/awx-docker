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

Dagger is the main command surface. Just is only a small convenience layer for
common local commands.

## Component Versions

Tracked defaults live in `components.toml`. That file pins the upstream AWX
source, AWX UI source, base image, receptor image, local image tag, platform,
and the dependency control files this wrapper owns.

Dagger reads those defaults through the Python config layer and passes them to
the Dockerfile as build arguments. The Dockerfile keeps matching `ARG` defaults
only as a direct `docker build` fallback; it cannot source `components.toml`
before `ARG` and `FROM` are evaluated.

Use `docker/awx/constraints/awx-python.yaml` for intentional AWX control-plane
Python overrides. Upstream AWX requirements remain the primary dependency
contract; exact pins in this constraints file either constrain upstream
resolution or fail the build when incompatible.

Job Ansible and collection versions should be controlled by the execution
environment image selected by AWX job templates, not by the AWX web/task image.
This wrapper does not build EE images yet.

## Requirements

- Docker or another BuildKit-capable container builder
- Dagger
- Just for local command aliases
- uv with Python 3.12 for local tests outside Dagger

## Build And Verify

```bash
# Run formatting, lint, shell, workflow, and unit checks.
dagger call check --source=.

# Resolve an AWX branch, tag, or commit to a concrete SHA.
dagger call resolve-ref --source=. --upstream-ref=devel

# Build the image.
dagger call build --source=. --upstream-ref=devel --awx-ui-ref=v2.4.313

# Build the image and run the runtime contract check.
dagger call verify --source=. --upstream-ref=devel --awx-ui-ref=v2.4.313 export --path=build/evidence

# Export a verified image as an OCI tarball.
dagger call export --source=. --upstream-ref=devel --awx-ui-ref=v2.4.313 --image-ref=awx-devel:devel export --path=build/out/awx-devel.tar
```

The AWX UI source is pinned separately from the AWX server source. The default
is recorded in `components.toml`, and `--awx-ui-ref` can still override it for a
single Dagger call. Upstream AWX defaults to cloning `ansible-ui` from `main`
when building UI assets; this wrapper fetches `ansible-ui` at the configured UI
ref first so `make ui` builds from a known tag or commit instead of pulling the
moving branch.

## Example Compose Smoke Test

`compose.example.yaml` starts this image with local Postgres and Redis
containers. It is intended for a quick smoke test of a published or locally
built image, not as a supported production deployment.

```bash
cp .env.example .env
# Edit .env and replace every change-me value before starting the stack.
docker compose --env-file .env -f compose.example.yaml up -d
```

The example defaults to `ghcr.io/robarmstrong96/awx-docker:production`. To test a
local export or another registry tag, set `AWX_IMAGE` in `.env`.

## Example Podman Pod Smoke Test

`pod.example.yaml` starts the same basic smoke-test stack through
`podman kube play`: one pod with Postgres, Redis, and the AWX container. It uses
loopback addresses between containers because containers in a pod share one
network namespace.

Edit the `change-me` values in the file before use. The example publishes AWX
on `http://localhost:8014` so it can run next to the Compose example, which
defaults to port `8013`.

```bash
podman kube play --replace pod.example.yaml
podman pod logs -f awx-docker-example
podman kube play --down pod.example.yaml --force
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
just verify
just export
just clean
just distclean
```

Use Dagger directly when overriding build inputs:

```bash
dagger call build --source=. --upstream-ref=devel --awx-ui-ref=v2.4.313
dagger call export --source=. --image-ref=awx-devel:devel export --path=build/out/awx-devel.tar
```

## Defaults

- Component manifest: `components.toml`
- Upstream AWX repo: `https://github.com/ansible/awx.git`
- Upstream AWX ref: `devel`
- Upstream AWX UI repo: `https://github.com/ansible/ansible-ui.git`
- Upstream AWX UI ref: `v2.4.313`
- Base image: `quay.io/centos/centos:stream9`
- Receptor image: `quay.io/ansible/receptor:devel`
- AWX Python constraints: `docker/awx/constraints/awx-python.yaml`
- Local image tag: `awx-devel:devel`
- Dockerfile: `docker/awx/Dockerfile`

## Runtime Check

`verify` runs `docker/awx/bin/verify-runtime-contract` inside the built image.
That check confirms the copied AWX source, wrapper entrypoint, supervisor
configuration, `awx-manage`, source revision files, and license files are
present.

## Notices

Wrapper files in this repository are licensed under Apache-2.0. Built images
include upstream AWX source and retain upstream license and source revision
metadata under `/usr/share/licenses/awx-wrapper/`.
