# Private Image Workflow

Use the manual `Private image` workflow to prove the Docker-capable build gate for this wrapper.

## Repository Setup

If the wrapper has not been pushed yet, create the remote under the intended owner and push the `development` branch:

```bash
gh repo create OWNER/awx-docker --private --source=. --remote=origin --push
```

The repository can be made public later, but keep the image package private until [licensing.md](licensing.md) is satisfied.

## Run Without Pushing

Start with `publish_image=false` so the runner builds and verifies the image without publishing it:

```bash
gh workflow run "Private image" \
  --ref development \
  -f awx_ref=devel \
  -f image_tag=devel \
  -f publish_image=false
```

Watch the latest run:

```bash
gh run list --workflow "Private image" --limit 1
gh run watch RUN_ID --exit-status
```

Download the evidence artifact:

```bash
gh run download RUN_ID --name awx-image-build-evidence --dir build/evidence/runner
```

## Required Evidence

The run proves the Docker-capable build gate only when all of the following are true:

- The workflow conclusion is `success`.
- `build-metadata.env` records the requested AWX ref, resolved AWX SHA, image name/tag, wrapper revision, and platform.
- `runner-diagnostics.env` records Docker and Buildx availability on the runner after the workflow's bounded runner disk cleanup step.
- `docker-build.log` exists for the image build step.
- `image-verification.env` contains `VERIFICATION_STATUS=passed`.
- `image-verification.env` contains the same AWX SHA for `AWX_EXPECTED_REF`, `AWX_IMAGE_REF`, and `AWX_LABEL_REF`.
- `image-verification.env` contains `AWX_GIT_METADATA=absent`.

Do not treat static workflow artifacts as image-build proof. They are useful pre-build evidence only.

## Private Push

After a no-push run succeeds and package visibility is confirmed private, rerun with `publish_image=true`:

```bash
gh workflow run "Private image" \
  --ref development \
  -f awx_ref=devel \
  -f image_tag=devel \
  -f publish_image=true
```

The workflow verifies the local image before the push step. Public package visibility remains blocked until the licensing gate is complete.
