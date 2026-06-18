# AWX Docker Image Builder

This repo builds an unofficial AWX development image from upstream AWX.

It does not vendor AWX. The `Dockerfile` clones `ansible/awx` during the Docker build.

## Basic Use

```bash
make preflight
make build
make verify-image
```

Default output:

```text
awx-devel:devel
```

To build a registry tag:

```bash
IMAGE_NAME=ghcr.io/YOUR_ORG/awx-devel IMAGE_TAG=devel make build
make verify-image
```

Push is separate on purpose:

```bash
IMAGE_NAME=ghcr.io/YOUR_ORG/awx-devel IMAGE_TAG=devel make push
```

## Useful Commands

```bash
make doctor
make preflight
make resolve-ref
make build
make verify-image
make push
make print-tags
```

## Notes

- This is not an official AWX, Ansible, or Red Hat image.
- AWX upstream still recommends the AWX Operator for real deployments.
- Wrapper files in this repo are licensed under Apache-2.0.
- Built images include AWX source from `ansible/awx` and retain the AWX license and source revision in `/usr/share/licenses/awx-wrapper/`.
