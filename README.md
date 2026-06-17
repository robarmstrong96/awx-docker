# AWX Docker Image Builder

This repo builds a private, unofficial AWX development image from upstream AWX.

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

To build a private registry tag:

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
make public-hygiene
make resolve-ref
make build
make verify-image
make push
make print-tags
```

## Notes

- Keep the repo and image private for now.
- Do not publish publicly until [docs/licensing.md](docs/licensing.md) is handled.
- This is not an official AWX, Ansible, or Red Hat image.
- AWX upstream still recommends the AWX Operator for real deployments.

The manual GitHub workflow can build and verify the image without pushing it. See [docs/private-image-workflow.md](docs/private-image-workflow.md) only if you need to rerun that workflow.
