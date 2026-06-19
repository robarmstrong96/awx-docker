# Licensing

Wrapper code in this repository is licensed under Apache-2.0.

AWX is developed by the upstream AWX project and is licensed separately. This
project clones AWX during image build instead of storing AWX source in this
repository.

Built images include upstream AWX source. The image build copies the upstream
AWX license and source revision metadata into `/usr/share/licenses/awx-wrapper/`.

Do not use AWX, Ansible, or Red Hat logos. Do not imply official support,
endorsement, or production readiness.
