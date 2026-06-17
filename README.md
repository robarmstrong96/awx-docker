# AWX Docker Self-Host Lab

This repo wraps AWX's upstream `devel` branch Docker Compose development environment for local self-hosting experiments.

AWX upstream still recommends the AWX Operator for real installs. Their Docker Compose path is development/test-oriented and `devel` is not stable, so treat this as a lab environment until it proves itself.

## Requirements

- Docker with the Compose plugin
- Git
- Make
- Ansible (`ansible-playbook` and `ansible-galaxy`)
- OpenSSL

## Quick Start

```bash
cp .env.example .env
make doctor
make bootstrap
make render
make up
make admin-password
```

AWX should be reachable at:

```text
http://localhost:8013
```

Username:

```text
admin
```

`make admin-password` prints the generated password unless `ADMIN_PASSWORD` was set before the first render/start.

## Common Commands

```bash
make doctor          # Check local dependencies
make bootstrap       # Clone upstream AWX devel into upstream/awx
make update          # Fast-forward the upstream checkout
make render          # Render AWX's generated compose/config sources
make up              # Start detached using the published devel image
make up-build        # Build the local awx_devel image, then start detached
make logs            # Follow compose logs
make ps              # Show compose service state
make down            # Stop containers
make clean-containers
```

Volume cleanup is intentionally guarded:

```bash
CONFIRM=delete-awx-volumes make clean-volumes
```

## Layout

- `scripts/awx-compose.sh` is the control wrapper.
- `${XDG_CACHE_HOME:-$HOME/.cache}/awx-docker/awx` is the default upstream checkout path.
- `$AWX_DIR/tools/docker-compose/_sources/` contains AWX-generated compose files, secrets, and runtime config after `make render` or `make up`.
- `AWX_DIR` must point outside this repo. The wrapper refuses nested AWX checkouts unless `ALLOW_AWX_DIR_INSIDE_REPO=true` is set explicitly.

## Notes

- The default path uses `ghcr.io/ansible/awx_devel:devel`. Run `make up-build` when you need an image built from the checked-out source.
- AWX's generated compose uses fixed container and volume names prefixed with `tools_`, so avoid running multiple copies on the same Docker host.
- The generated admin password and service secrets live under the ignored upstream checkout. Back them up before deleting volumes or `_sources` if you care about preserving the lab instance.
