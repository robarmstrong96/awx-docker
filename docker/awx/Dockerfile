# syntax=docker/dockerfile:1.7
# Use a Dockerfile version that supports the SSH mount below.

# ----- Build arguments --------------------------------------------------------

# Dagger passes these from components.toml. The defaults below are only a
# direct docker-build fallback, and unit tests keep them aligned with the
# manifest because Dockerfiles cannot source TOML before ARG/FROM evaluation.
ARG CENTOS_STREAM_IMAGE=quay.io/centos/centos:stream9
ARG AWX_REPO=https://github.com/ansible/awx.git
ARG AWX_REF=devel
ARG AWX_REQUESTED_REF=devel
ARG AWX_SOURCE_REVISION=unknown
ARG AWX_UI_REPO=https://github.com/ansible/ansible-ui.git
ARG AWX_UI_REF=v2.4.313
ARG RECEPTOR_IMAGE=quay.io/ansible/receptor:devel
ARG AWX_PYTHON_CONSTRAINTS=awx-python.yaml

# ----- Receptor binary --------------------------------------------------------

FROM ${RECEPTOR_IMAGE} AS receptor

# ----- AWX source -------------------------------------------------------------

FROM ${CENTOS_STREAM_IMAGE} AS awx-source
ARG AWX_REPO
ARG AWX_REF
ARG AWX_REQUESTED_REF

# Install packages before cloning AWX so normal source changes rebuild less.
COPY docker/awx/bin/install-rpms /usr/local/libexec/awx-docker/install-rpms
COPY docker/awx/bin/prepare-awx-source /usr/local/libexec/awx-docker/prepare-awx-source
COPY docker/awx/packages/source.rpms /tmp/packages.rpms
RUN /usr/local/libexec/awx-docker/install-rpms /tmp/packages.rpms
RUN /usr/local/libexec/awx-docker/prepare-awx-source

# ----- UI assets --------------------------------------------------------------

FROM ${CENTOS_STREAM_IMAGE} AS ui-builder
ARG AWX_UI_REPO
ARG AWX_UI_REF

USER root
COPY docker/awx/bin/install-rpms /usr/local/libexec/awx-docker/install-rpms
COPY docker/awx/bin/prepare-awx-ui-source /usr/local/libexec/awx-docker/prepare-awx-ui-source
COPY docker/awx/packages/ui-builder.rpms /tmp/packages.rpms
RUN INSTALL_RPMS_ENABLE_NODEJS18=true \
    /usr/local/libexec/awx-docker/install-rpms /tmp/packages.rpms

COPY --from=awx-source /awx-src /tmp/src
WORKDIR /tmp/src
RUN /usr/local/libexec/awx-docker/prepare-awx-ui-source
RUN make ui

# ----- Python packages --------------------------------------------------------

FROM ${CENTOS_STREAM_IMAGE} AS builder

ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8 \
    AWX_LOGGING_MODE=stdout

USER root

COPY docker/awx/bin/install-rpms /usr/local/libexec/awx-docker/install-rpms
COPY docker/awx/bin/install-awx-python-deps /usr/local/libexec/awx-docker/install-awx-python-deps
COPY docker/awx/packages/python-builder.rpms /tmp/packages.rpms
RUN /usr/local/libexec/awx-docker/install-rpms /tmp/packages.rpms

ARG VERSION
ARG SETUPTOOLS_SCM_PRETEND_VERSION
ARG AWX_PYTHON_CONSTRAINTS

# Copy only the files needed to install Python packages.
# The finished Python environment is copied into the final image later.
COPY --from=awx-source /awx-src/Makefile /tmp/Makefile
RUN mkdir /tmp/requirements
COPY --from=awx-source /awx-src/requirements/requirements.txt /tmp/requirements/requirements.txt
COPY --from=awx-source /awx-src/requirements/requirements_tower_uninstall.txt /tmp/requirements/requirements_tower_uninstall.txt
COPY --from=awx-source /awx-src/requirements/requirements_git.txt /tmp/requirements/requirements_git.txt
COPY --from=awx-source /awx-src/requirements/requirements_dev.txt /tmp/requirements/requirements_dev.txt
COPY docker/awx/constraints /tmp/requirements/constraints

WORKDIR /tmp
RUN --mount=type=ssh AWX_PYTHON_CONSTRAINTS="/tmp/requirements/constraints/${AWX_PYTHON_CONSTRAINTS}" \
    /usr/local/libexec/awx-docker/install-awx-python-deps

# ----- Final image ------------------------------------------------------------

FROM ${CENTOS_STREAM_IMAGE}

ARG AWX_REPO
ARG AWX_REQUESTED_REF
ARG AWX_SOURCE_REVISION
ARG AWX_UI_REPO
ARG AWX_UI_REF
ARG RECEPTOR_IMAGE
ARG AWX_PYTHON_CONSTRAINTS
ARG INSTALL_PYTHON_DEBUGINFO=false

ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8 \
    AWX_LOGGING_MODE=stdout \
    HOME=/var/lib/awx \
    PATH="/var/lib/awx/venv/awx/bin/:${PATH}" \
    SETUPTOOLS_SCM_PRETEND_VERSION="0.0.dev0+g${AWX_SOURCE_REVISION}" \
    SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AWX="0.0.dev0+g${AWX_SOURCE_REVISION}"

LABEL org.opencontainers.image.title="Unofficial AWX proof-of-concept image" \
      org.opencontainers.image.description="AWX POC image built by cloning upstream AWX" \
      org.opencontainers.image.source="https://github.com/ansible/awx" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.vendor="unofficial" \
      dev.awx-wrapper.awx.repo="${AWX_REPO}" \
      dev.awx-wrapper.awx.requested-ref="${AWX_REQUESTED_REF}" \
      dev.awx-wrapper.awx.resolved-revision="${AWX_SOURCE_REVISION}" \
      dev.awx-wrapper.awx-ui.repo="${AWX_UI_REPO}" \
      dev.awx-wrapper.awx-ui.ref="${AWX_UI_REF}" \
      dev.awx-wrapper.receptor.image="${RECEPTOR_IMAGE}" \
      dev.awx-wrapper.python.constraints="${AWX_PYTHON_CONSTRAINTS}"

USER root

# ----- OS packages ------------------------------------------------------------

COPY docker/awx/bin/install-rpms /usr/local/libexec/awx-docker/install-rpms
COPY docker/awx/bin/synthesize-awx-dist-info /usr/local/libexec/awx-docker/synthesize-awx-dist-info
COPY docker/awx/bin/prepare-runtime-layout /usr/local/libexec/awx-docker/prepare-runtime-layout
COPY docker/awx/bin/verify-awx-python-contract /usr/local/libexec/awx-docker/verify-awx-python-contract
COPY docker/awx/bin/verify-runtime-contract /usr/local/libexec/awx-docker/verify-runtime-contract
COPY docker/awx/repos/ansible-rsyslog-epel-9.repo /etc/yum.repos.d/ansible-Rsyslog-epel-9.repo
COPY docker/awx/packages/runtime.rpms /tmp/packages.rpms
RUN INSTALL_RPMS_ENABLE_NODEJS18=true INSTALL_RPMS_INSTALL_INOTIFY=true \
    /usr/local/libexec/awx-docker/install-rpms /tmp/packages.rpms

# ----- Python tools -----------------------------------------------------------

RUN pip3.12 install -vv --no-cache-dir virtualenv supervisor dumb-init build
RUN pip3.12 install -vv --no-cache-dir git+https://github.com/coderanger/supervisor-stdout.git@973ba19967cdaf46d9c1634d1675fc65b9574f6e
RUN pip3.12 install -vv --no-cache-dir black setuptools-scm
RUN if [ "$INSTALL_PYTHON_DEBUGINFO" = "true" ]; then \
      dnf --enablerepo=baseos-debug -y install python3-debuginfo && dnf -y clean all; \
    fi
RUN rm -rf /root/.cache && rm -rf /tmp/*

# ----- AWX runtime files ------------------------------------------------------

COPY --from=builder /var/lib/awx /var/lib/awx
COPY --from=receptor /usr/bin/receptor /usr/bin/receptor

# ----- AWX development source -------------------------------------------------

# AWX's dev startup scripts look for the source tree at this path.
# Copy it into the image, then remove Git history.
COPY --from=ui-builder /tmp/src /awx_devel
RUN rm -rf /awx_devel/.git /awx_devel/awx/ui/src/.git

# ----- Licenses and source info ----------------------------------------------

RUN mkdir -p /usr/share/licenses/awx-wrapper && \
    cp /awx_devel/LICENSE.md /usr/share/licenses/awx-wrapper/AWX-LICENSE.md && \
    cp /awx_devel/.awx_source_revision /usr/share/licenses/awx-wrapper/AWX-SOURCE-REVISION && \
    cp /awx_devel/.awx_requested_ref /usr/share/licenses/awx-wrapper/AWX-REQUESTED-REF

# ----- Command links ----------------------------------------------------------

RUN ln -s /var/lib/awx/venv/awx/bin/awx-manage /usr/bin/awx-manage

# ----- Development TLS certificate -------------------------------------------

RUN openssl req -nodes -newkey rsa:2048 -keyout /etc/nginx/nginx.key -out /etc/nginx/nginx.csr \
        -subj "/C=US/ST=North Carolina/L=Durham/O=Ansible/OU=AWX Development/CN=awx.localhost" && \
    openssl x509 -req -days 365 -in /etc/nginx/nginx.csr -signkey /etc/nginx/nginx.key -out /etc/nginx/nginx.crt && \
    chmod 640 /etc/nginx/nginx.csr /etc/nginx/nginx.key /etc/nginx/nginx.crt

# ----- Container tools --------------------------------------------------------

RUN rpm --restore shadow-utils 2>/dev/null || :
RUN sed -i -e 's|^#mount_program|mount_program|g' -e '/additionalimage.*/a "/var/lib/shared",' -e 's|^mountopt[[:space:]]*=.*$|mountopt = "nodev,fsync=0"|g' /etc/containers/storage.conf
ENV _CONTAINERS_USERNS_CONFIGURED=""
RUN mkdir -p /etc/containers/registries.conf.d/ && \
    echo "unqualified-search-registries = []" >> /etc/containers/registries.conf.d/force-fully-qualified-images.conf && \
    chmod 644 /etc/containers/registries.conf.d/force-fully-qualified-images.conf

COPY --from=awx-source /awx-src/tools/ansible/roles/dockerfile/files/rsyslog.conf /var/lib/awx/rsyslog/rsyslog.conf

# ----- AWX startup files ------------------------------------------------------

COPY --from=awx-source /awx-src/tools/ansible/roles/dockerfile/files/wait-for-migrations /usr/local/bin/wait-for-migrations
COPY --from=awx-source /awx-src/tools/ansible/roles/dockerfile/files/stop-supervisor /usr/local/bin/stop-supervisor
COPY --from=awx-source /awx-src/tools/ansible/roles/dockerfile/files/uwsgi.ini /etc/tower/uwsgi.ini

COPY --from=awx-source /awx-src/tools/docker-compose/launch_awx.sh /usr/bin/launch_awx.sh
COPY --from=awx-source /awx-src/tools/docker-compose/start_tests.sh /start_tests.sh
COPY --from=awx-source /awx-src/tools/docker-compose/bootstrap_development.sh /usr/bin/bootstrap_development.sh
COPY --from=awx-source /awx-src/tools/docker-compose/entrypoint.sh /entrypoint.sh
COPY --from=awx-source /awx-src/tools/docker-compose/supervisor.conf /etc/supervisord.conf
COPY --from=awx-source /awx-src/tools/scripts/config-watcher /usr/bin/config-watcher
COPY scripts/runtime-entrypoint.sh /usr/local/bin/awx-wrapper-entrypoint
COPY docker/awx/rootfs/ /

# ----- Runtime layout ---------------------------------------------------------

# AWX startup expects Python package info next to the copied source.
# Create that info after Git history is removed.
RUN /usr/local/libexec/awx-docker/synthesize-awx-dist-info "${AWX_SOURCE_REVISION}"
RUN /usr/local/libexec/awx-docker/prepare-runtime-layout

WORKDIR /awx_devel

# ----- Network and startup ----------------------------------------------------

# AWX uses 8043 for HTTPS and 8013 for websocket traffic.
# Keep 8080 and 22 for AWX dev-tool compatibility.
EXPOSE 8043 8013 8080 22

ENTRYPOINT ["/usr/local/bin/awx-wrapper-entrypoint"]
CMD ["/usr/bin/launch_awx.sh", "supervisord", "--pidfile=/tmp/supervisor_pid", "-n"]
