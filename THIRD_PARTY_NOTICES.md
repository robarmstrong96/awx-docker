# Third-Party Notices

Built images include source and runtime dependencies from upstream AWX and its
dependency graph. This repository does not vendor those projects.

The image build preserves the upstream AWX license file and source revision in:

- `/usr/share/licenses/awx-wrapper/AWX-LICENSE.md`
- `/usr/share/licenses/awx-wrapper/AWX-REQUESTED-REF`
- `/usr/share/licenses/awx-wrapper/AWX-SOURCE-REVISION`

Review upstream AWX and dependency licensing before publishing images outside a
controlled environment.
