# AWX Image Builder

Private image-builder wrapper for AWX `devel`.

This repo does not vendor AWX and does not keep an AWX checkout on the host. The repo-owned `Dockerfile` clones `ansible/awx` during Docker build, prepares the AWX development runtime in the image, and leaves deployment composition to the target environment.

The deployment environment owns the runtime compose file and should wire this image to its existing Postgres and Redis services.

## Status

Milestone 1 is private image building. Keep the repo and published image private until the licensing, SBOM, notices, and trademark review gates are complete.

AWX upstream still recommends the AWX Operator for real installs. This image follows AWX's development-container model and is an experiment for self-hosted Docker use.

## Build

```bash
cp .env.example .env
make preflight
make resolve-ref
make write-metadata
make build
make verify-image
```

Useful overrides:

```bash
AWX_REF=devel IMAGE_NAME=ghcr.io/YOUR_ORG/awx-devel IMAGE_TAG=devel make build
AWX_REF=<commit-sha> IMAGE_TAG=<commit-sha> make build
```

Print the tag that will be built:

```bash
make print-tags
```

Push is explicit and verifies the local image before publishing:

```bash
make build
make verify-image
make push
```

## Commands

```bash
make doctor      # Check Docker and basic host dependencies
make preflight   # Static checks that do not require Docker
make resolve-ref # Resolve AWX_REF to the exact upstream commit SHA
make write-metadata # Write build metadata under build/evidence/
make build       # Build the private AWX image
make verify-image # Verify embedded AWX source revision and required files
make push        # Push the already-built image tag
make print-tags  # Print IMAGE_NAME:IMAGE_TAG
```

## Image Contract

The image embeds AWX source at:

```text
/awx_devel
```

The image includes AWX's development startup entrypoint and supervisor config from upstream. Runtime config is intentionally not owned here yet. A deployment compose file must provide the AWX database, Redis/socket wiring, secrets, Django config, and any environment required by the target host.

See [docs/runtime-contract.md](docs/runtime-contract.md) for the handoff contract. That document is intentionally not a compose file.

Current image labels include the wrapper revision and requested AWX repo/ref. The image also copies AWX's Apache-2.0 license and the resolved source revision into:

```text
/usr/share/licenses/awx-wrapper/
```

Local and CI builds write compact audit evidence under:

```text
build/evidence/
```

The manual GitHub workflow uploads that directory as `awx-image-build-evidence`.

## Licensing

Do not publish this image publicly until [docs/licensing.md](docs/licensing.md) is satisfied. AWX is Apache-2.0, but the complete image also includes OS packages, Python dependencies, npm assets, generated UI assets, and trademarks/branding that need review.

This project is unofficial and is not affiliated with or endorsed by Red Hat, Ansible, or the AWX project.
