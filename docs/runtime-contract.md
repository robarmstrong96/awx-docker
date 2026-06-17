# Runtime Contract

The deployment environment owns the runtime compose file. This repository only builds the AWX image.

## Image Inputs

Use a private image tag produced by this repo:

```text
ghcr.io/<private-owner>/awx-devel:<tag>
```

Prefer immutable tags based on the resolved AWX commit SHA once the build is verified.

## Expected Container Shape

The image embeds AWX source at:

```text
/awx_devel
```

The default entrypoint is AWX's development entrypoint:

```text
/entrypoint.sh
```

The intended command mirrors upstream's development container:

```text
launch_awx.sh supervisord --pidfile=/tmp/supervisor_pid -n
```

## External Services

The deployment environment should provide existing external services instead of starting Postgres or Redis from this repository.

Required runtime wiring:

- PostgreSQL connection settings for AWX.
- Redis settings or socket wiring compatible with AWX's development settings.
- Persistent AWX secret key.
- Broadcast websocket secret.
- Receptor config at `/etc/receptor/receptor.conf`.
- AWX Django config under `/etc/tower/conf.d/`.
- Nginx config if using the upstream dev nginx/supervisor process.

The upstream Docker Compose development environment generated these files under `tools/docker-compose/_sources/`; the deployment environment should own equivalent runtime config and secrets.

## Ports

The image exposes the same development ports as upstream:

```text
8013  HTTP
8043  HTTPS
8080  debug/unused upstream mapping
22    receptor/ssh-style service port
```

## Open Runtime Questions

- Whether Redis is provided through TCP settings or a Unix socket mount.
- Whether nginx should run inside this container or be handled by ingress/proxying.
- Whether the first private runtime should set `RUN_MIGRATIONS=1` or run migrations as a one-shot task.
- Which persistent volumes are needed for projects, receptor runtime files, and AWX-local container storage.

These questions belong to the deployment compose/runtime milestone, not the private image-builder milestone.

