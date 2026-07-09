# syntax=docker/dockerfile:1.7
# Use a Dockerfile version that supports the SSH mount below.

# ----- Build arguments --------------------------------------------------------

# Dagger normally passes these from config/components/components.toml. Keep the
# defaults here for direct docker builds; Docker cannot read TOML before
# ARG/FROM evaluation.
ARG CENTOS_STREAM_IMAGE=quay.io/centos/centos:stream9
ARG AWX_REPO=https://github.com/ansible/awx.git
ARG AWX_REF=devel
ARG AWX_REQUESTED_REF=devel
ARG AWX_UI_REPO=https://github.com/ansible/ansible-ui.git
ARG AWX_UI_REF=v2.4.313

# ----- AWX source -------------------------------------------------------------

FROM ${CENTOS_STREAM_IMAGE} AS awx-source
ARG AWX_REPO
ARG AWX_REF
ARG AWX_REQUESTED_REF

COPY docker/awx/bin/install-rpms /usr/local/libexec/awx-docker/install-rpms
COPY docker/awx/bin/prepare-awx-source /usr/local/libexec/awx-docker/prepare-awx-source
COPY docker/awx/packages/source.rpms /tmp/packages.rpms
RUN /usr/local/libexec/awx-docker/install-rpms /tmp/packages.rpms
RUN /usr/local/libexec/awx-docker/prepare-awx-source

# ----- UI bundle --------------------------------------------------------------

FROM ${CENTOS_STREAM_IMAGE}
ARG AWX_UI_REPO
ARG AWX_UI_REF
ARG AWX_UI_DELIVERY=embedded

COPY docker/awx/bin/install-rpms /usr/local/libexec/awx-docker/install-rpms
COPY docker/awx-ui/bin/export-static-bundle /usr/local/libexec/awx-docker/export-awx-ui-static-bundle
COPY docker/awx-ui/bin/install-build-deps /usr/local/libexec/awx-docker/install-awx-ui-build-deps
COPY docker/awx-ui/bin/prepare-delivery /usr/local/libexec/awx-docker/prepare-awx-ui-delivery
COPY docker/awx-ui/bin/prepare-source /usr/local/libexec/awx-docker/prepare-awx-ui-source
COPY docker/awx-ui/bin/verify-static-bundle /usr/local/libexec/awx-docker/verify-awx-ui-static-bundle
COPY docker/awx-ui/packages/build.rpms /tmp/packages.rpms
RUN /usr/local/libexec/awx-docker/install-awx-ui-build-deps

COPY --from=awx-source /awx-src /tmp/src
WORKDIR /tmp/src
RUN /usr/local/libexec/awx-docker/prepare-awx-ui-delivery
RUN /usr/local/libexec/awx-docker/export-awx-ui-static-bundle
RUN /usr/local/libexec/awx-docker/verify-awx-ui-static-bundle
