# AWX Docker Proof-of-Concept Image Builder

This repo builds an unofficial AWX image for local testing and CI. It is not
from Red Hat, Ansible, or the AWX project, and it is not meant for production.
For normal AWX installs, use the AWX Operator.

## What It Builds

- `docker/awx`: AWX control-plane image.
- `docker/awx-ui`: static AWX UI bundle for sideloaded UI runs.
- `docker/awx-ee`: starter execution environment image for jobs.

Dagger does the real work. Just is there so the common commands are shorter.

## Requirements

- Docker or another BuildKit-capable container builder
- Dagger
- Just if you want shorter commands
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

Just runs the same default commands:

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

Use Dagger directly for the few runtime-only options:

```bash
dagger call export --source=. --image-ref=awx-devel:devel export --path=build/out/awx-devel.tar
dagger call export-ee --source=. --image-ref=awx-ee:devel export --path=build/out/awx-ee.tar
```

Edit `config/components/components.toml` for version and image choices like AWX
refs, UI refs, base images, platforms, receptor, and EE defaults.

## Configuration

Most defaults live in `config/components/components.toml`: AWX refs, image
names, base images, platform, receptor, EE defaults, and local tooling.

AWX Python pins live in `config/awx/constraints/awx-python.yaml`. AWX already
has its own requirements, so leave this empty unless we need to force one of
those packages to a specific version.

The starter EE lives in `docker/awx-ee/execution-environment.yml`. Collections
go in `docker/awx-ee/requirements.yml`, extra Python packages go in
`docker/awx-ee/requirements.txt`, and extra RPM packages go in
`docker/awx-ee/bindep.txt`.

## UI Delivery

The default `embedded` mode puts the pinned AWX UI inside the AWX image. Use
`sideloaded` when you want the AWX runtime image and UI bundle built separately:

```bash
dagger call export \
  --source=. \
  --image-ref=awx-devel:sideloaded \
  export --path=build/out/awx-devel-sideloaded.tar
```

Set `awx_ui.delivery = "sideloaded"` in `config/components/components.toml`
before building that image.

Then build the UI bundle and mount it at `/var/lib/awx/public/static`:

```bash
dagger call export-ui --source=. export --path=build/out/awx-ui-static
```

Nginx serves that directory for `/static`, `/locales`, and `/favicon.ico`. The
AWX image will not copy the UI bundle into place for you at startup.

## Local Smoke Tests

Compose embedded example:

```bash
cp config/examples/compose/.env.example config/examples/compose/.env
docker compose \
  --env-file config/examples/compose/.env \
  -f config/examples/compose/compose.example.yaml \
  up -d
```

Compose sideloaded example:

```bash
# In config/examples/compose/.env:
# AWX_SIDELOADED_IMAGE=awx-devel:sideloaded
# AWX_SIDELOADED_HTTP_PORT=8015
# AWX_UI_STATIC_BUNDLE=../../../build/out/awx-ui-static
docker compose \
  --env-file config/examples/compose/.env \
  -f config/examples/compose/compose.sideloaded.example.yaml \
  up -d
```

Podman embedded example:

```bash
podman kube play --replace config/examples/podman/pod.example.yaml
podman pod logs -f awx-docker-example
podman kube play --down config/examples/podman/pod.example.yaml --force
```

Podman sideloaded example:

```bash
# First edit pod.sideloaded.example.yaml and replace the hostPath with a real
# absolute path to build/out/awx-ui-static.
podman kube play --replace config/examples/podman/pod.sideloaded.example.yaml
podman pod logs -f awx-docker-sideloaded-example
podman kube play --down config/examples/podman/pod.sideloaded.example.yaml --force
```

Replace the `change-me` values before starting any example. Embedded Compose
uses `http://localhost:8013`, embedded Podman uses `http://localhost:8014`, and
the sideloaded examples use `http://localhost:8015` unless you change the port.

Example browser snapshots from the Podman pod:

- [Login screen](docs/snapshots/awx-pod-login.png)
- [Overview dashboard](docs/snapshots/awx-pod-dashboard.png)
- [Jobs list](docs/snapshots/awx-pod-jobs.png)

## Notes

### Upstream AWX is fetched during the build

We do not keep AWX source in this repo. The Docker build clones the AWX ref from
`components.toml`, writes the resolved commit into the image, and keeps the
source/license notes under `/usr/share/licenses/awx-wrapper/`.

### The Dockerfile still has defaults

`config/components/components.toml` is the main source of truth. Dagger reads it
and passes those values as build args instead of exposing a giant pile of
function parameters. The Dockerfile still has matching `ARG` defaults because
plain `docker build` needs something to use before Docker can evaluate `FROM`.

### AWX UI is pinned separately

AWX normally pulls `ansible-ui` while building the UI. We check out the UI ref
first, so the UI comes from a known tag or commit instead of a moving branch.
The separate `docker/awx-ui` build lets one AWX runtime image use different UI
bundles.

### Job dependencies belong in the EE image

Do not put playbook Ansible versions, collections, or job-only Python packages
in the AWX web/task image. Put them in the EE image selected by the AWX job
template. The included EE is only a starter: it pins `ansible-core==2.15.13`
and `ansible-runner==2.4.0`, then installs the collections in
`docker/awx-ee/requirements.yml`.

### The Podman example is a smoke test

The AWX container is privileged because AWX starts Podman containers for job
EEs. Rootless Podman can work if the host allows privileged rootless containers.
Deeply nested dev setups, like Podman inside Podman inside Docker, may need
local storage or cgroup tweaks that normal host Podman should not need.

### `verify` checks the wrapper contract

`dagger call verify --source=.` builds the AWX image and runs
`docker/awx/bin/verify-runtime-contract` inside it. It checks that the copied
AWX source, wrapper entrypoint, supervisor config, `awx-manage`, source
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

Wrapper files in this repo are Apache-2.0. Built images include upstream AWX
source and keep upstream license/source metadata under
`/usr/share/licenses/awx-wrapper/`.
