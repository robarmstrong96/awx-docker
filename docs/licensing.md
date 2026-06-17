# Licensing Gate

This project must stay private until the public-release gates below are complete.

## Required Before Public Release

- Preserve AWX's Apache-2.0 license in the image and repository documentation.
- Preserve required copyright, trademark, and attribution notices from AWX source.
- Add prominent notices for any modified AWX files if we start patching upstream source.
- Generate an SBOM for every published image.
- Generate a third-party license report for OS, Python, and JavaScript dependencies included in the image.
- Review AWX/Ansible/Red Hat trademark usage and avoid implying the image is official.
- Avoid AWX/Ansible logos in this repo or package branding unless trademark guidance explicitly allows the use.
- Add OCI labels for wrapper source, wrapper revision, upstream AWX repo, upstream AWX ref, and resolved upstream AWX SHA.
- Confirm the private image can be rebuilt reproducibly from `AWX_REF`.
- Add a manual approval gate before any public package visibility change.

## Current Private Position

The current image builder is intended for private testing only. It clones AWX during Docker build and records the resolved AWX revision in `/usr/share/licenses/awx-wrapper/AWX-SOURCE-REVISION` inside the image.

The current repository and image naming must describe this as an unofficial builder/image. Do not use language that suggests endorsement by Red Hat, Ansible, or AWX.

