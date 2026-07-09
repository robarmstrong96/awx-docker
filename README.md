# AWX Docker Proof-of-Concept Image Builder

This repo builds an unofficial AWX image for local testing and CI experiments.
It is not affiliated with Red Hat, Ansible, or the AWX project, and it is not a
production install path. For real AWX lifecycle management, use the AWX
Operator.

## What It Builds

- `docker/awx`: AWX control-plane image.
- `docker/awx-ui`: static AWX UI bundle for sideloaded UI runs.
- `docker/awx-ee`: starter execution environment image for jobs.

Dagger is the build surface. Just is only a short alias layer around common
Dagger calls.

## Requirements

- Docker or another BuildKit-capable container builder
- Dagger
- Just, optional but convenient
- uv with Python 3.12 for local checks outside Dagger

## Commands

```bash
dagger call check --source=.
dagger call resolve-ref --source=. --upstream-ref=devel

dagger call build --source=.
dagger call verify --source=.
dagger call export --source=. export --path=build/out/awx-devel.tar

dagger call build-ui --source=.
dagger call export-ui --source=. export --path=build/out/awx-ui-static

dagger call build-ee --source=.
dagger call export-ee --source=. export --path=build/out/awx-ee.tar
```

The same defaults are available through Just:

```bash
just check
just build
just verify
just export
just build-ui
just export-ui
just build-ee
just export-ee
```

Use Dagger directly when overriding inputs:

```bash
dagger call build --source=. --upstream-ref=devel --awx-ui-ref=v2.4.313
dagger call export --source=. --image-ref=awx-devel:devel export --path=build/out/awx-devel.tar
dagger call export-ui --source=. --awx-ui-ref=v2.4.313 export --path=build/out/awx-ui-static
dagger call export-ee --source=. --image-ref=awx-ee:devel export --path=build/out/awx-ee.tar
```

## Configuration

Most defaults live in `config/components/components.toml`: upstream AWX, AWX UI,
image tags, base images, platform, receptor, EE defaults, and local tooling.

AWX control-plane Python pins live in
`config/awx/constraints/awx-python.yaml`. AWX already ships its own Python
requirements, so only add pins there when this wrapper needs to force one of
those packages to a specific version.

The starter EE is defined in `docker/awx-ee/execution-environment.yml`.
Collections go in `docker/awx-ee/requirements.yml`, extra Python packages go in
`docker/awx-ee/requirements.txt`, and extra RPM packages go in
`docker/awx-ee/bindep.txt`.

## UI Delivery

The default `embedded` mode builds the pinned AWX UI into the AWX image. For a
runtime image that can accept a separately built UI bundle, export the AWX image
with `sideloaded`:

```bash
dagger call export \
  --source=. \
  --awx-ui-delivery=sideloaded \
  --image-ref=awx-devel:sideloaded \
  export --path=build/out/awx-devel-sideloaded.tar
```

Then build the UI bundle and mount it at `/var/lib/awx/public/static`:

```bash
dagger call export-ui --source=. export --path=build/out/awx-ui-static
```

Nginx serves that directory for `/static`, `/locales`, and `/favicon.ico`. The
AWX image does not copy or sync sideloaded assets during startup.

## Local Smoke Tests

Compose example:

```bash
cp config/examples/compose/.env.example config/examples/compose/.env
docker compose \
  --env-file config/examples/compose/.env \
  -f config/examples/compose/compose.example.yaml \
  up -d
```

Podman pod example:

```bash
podman kube play --replace config/examples/podman/pod.example.yaml
podman pod logs -f awx-docker-example
podman kube play --down config/examples/podman/pod.example.yaml --force
```

Both examples need their `change-me` values replaced before use. Compose
defaults to `http://localhost:8013`; the Podman pod defaults to
`http://localhost:8014`.

Example browser snapshots from the Podman pod:

- [Login screen](docs/snapshots/awx-pod-login.png)
- [Overview dashboard](docs/snapshots/awx-pod-dashboard.png)
- [Jobs list](docs/snapshots/awx-pod-jobs.png)

## Notes

### Upstream AWX is fetched during the build

This wrapper intentionally stays thin. It does not vendor AWX source into this
repo. The Docker build clones the configured upstream AWX ref, records the
resolved commit in the image, and keeps source/license metadata under
`/usr/share/licenses/awx-wrapper/`.

### The Dockerfile still has defaults

`config/components/components.toml` is the normal source of truth. Dagger reads
it and passes the values as build args. The Dockerfile keeps matching `ARG`
defaults so a plain `docker build` still has a workable fallback; Docker cannot
read TOML before `ARG` and `FROM` are evaluated.

### AWX UI is pinned separately

Upstream AWX normally pulls `ansible-ui` while building UI assets. This wrapper
checks out the configured UI ref first, so the UI build comes from a known tag
or commit instead of a moving branch. The separate `docker/awx-ui` build exists
so the same AWX runtime image can be paired with different UI bundles.

### Job dependencies belong in the EE image

The AWX web/task image should not be where playbook Ansible versions,
collections, or job-only Python packages are managed. Put those in the
execution environment image selected by the AWX job template. The included EE
is just a starter: it pins `ansible-core==2.15.13` and
`ansible-runner==2.4.0`, then installs the collections listed in
`docker/awx-ee/requirements.yml`.

### The Podman example is a smoke test

The AWX container is privileged because AWX starts nested Podman containers for
execution environments. Rootless Podman can work when the host allows
privileged rootless containers. Deeply nested dev setups, such as Podman inside
Podman inside Docker, may need local storage or cgroup overrides that normal
host Podman runs should not need.

### `verify` checks the wrapper contract

`dagger call verify --source=.` builds the AWX image and runs
`docker/awx/bin/verify-runtime-contract` inside it. That check confirms the
copied AWX source, wrapper entrypoint, supervisor config, `awx-manage`, source
revision files, and license files are present.

## Defaults

- Component manifest: `config/components/components.toml`
- AWX: `https://github.com/ansible/awx.git`, ref `devel`
- AWX UI: `https://github.com/ansible/ansible-ui.git`, ref `v2.4.313`
- AWX UI delivery: `embedded`
- AWX image: `awx-devel:devel`
- AWX UI bundle output: `build/out/awx-ui-static`
- EE image: `awx-ee:devel`
- EE base image: `quay.io/ansible/ansible-runner:stable-2.15-devel`
- Base image: `quay.io/centos/centos:stream9`
- Receptor image: `quay.io/ansible/receptor:devel`
- AWX Python constraints: `config/awx/constraints/awx-python.yaml`

## Notices

Wrapper files in this repository are licensed under Apache-2.0. Built images
include upstream AWX source and retain upstream license and source revision
metadata under `/usr/share/licenses/awx-wrapper/`.
