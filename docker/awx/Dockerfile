# syntax=docker/dockerfile:1.7
# Uses the BuildKit Dockerfile frontend for RUN --mount=type=ssh.

# ----- Build arguments --------------------------------------------------------

ARG AWX_REPO=https://github.com/ansible/awx.git
ARG AWX_REF=devel
ARG AWX_REQUESTED_REF=devel
ARG AWX_SOURCE_REVISION=unknown
ARG RECEPTOR_IMAGE=quay.io/ansible/receptor:devel

# ----- Receptor binary --------------------------------------------------------

FROM ${RECEPTOR_IMAGE} AS receptor

# ----- AWX source checkout ----------------------------------------------------

FROM quay.io/centos/centos:stream9 AS awx-source
ARG AWX_REPO
ARG AWX_REF
ARG AWX_REQUESTED_REF

# Keep package installs before source checkout so base dependencies stay cacheable.
COPY docker/awx/bin/install-rpms /usr/local/libexec/awx-docker/install-rpms
COPY docker/awx/bin/prepare-awx-source /usr/local/libexec/awx-docker/prepare-awx-source
COPY docker/awx/packages/source.rpms /tmp/packages.rpms
RUN /usr/local/libexec/awx-docker/install-rpms /tmp/packages.rpms
RUN /usr/local/libexec/awx-docker/prepare-awx-source

# ----- UI assets --------------------------------------------------------------

FROM quay.io/centos/centos:stream9 AS ui-builder

USER root
COPY docker/awx/bin/install-rpms /usr/local/libexec/awx-docker/install-rpms
COPY docker/awx/packages/ui-builder.rpms /tmp/packages.rpms
RUN INSTALL_RPMS_ENABLE_NODEJS18=true \
    /usr/local/libexec/awx-docker/install-rpms /tmp/packages.rpms

COPY --from=awx-source /awx-src /tmp/src
WORKDIR /tmp/src
RUN make ui

# ----- Python dependency build ------------------------------------------------

FROM quay.io/centos/centos:stream9 AS builder

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8
ENV AWX_LOGGING_MODE=stdout

USER root

COPY docker/awx/bin/install-rpms /usr/local/libexec/awx-docker/install-rpms
COPY docker/awx/bin/install-awx-python-deps /usr/local/libexec/awx-docker/install-awx-python-deps
COPY docker/awx/packages/python-builder.rpms /tmp/packages.rpms
RUN /usr/local/libexec/awx-docker/install-rpms /tmp/packages.rpms

ARG VERSION
ARG SETUPTOOLS_SCM_PRETEND_VERSION

# AWX's Makefile owns requirement installation; keep build tools out of the
# final image while preserving the generated virtualenv.
COPY --from=awx-source /awx-src/Makefile /tmp/Makefile
RUN mkdir /tmp/requirements
COPY --from=awx-source /awx-src/requirements/requirements.txt /tmp/requirements/requirements.txt
COPY --from=awx-source /awx-src/requirements/requirements_tower_uninstall.txt /tmp/requirements/requirements_tower_uninstall.txt
COPY --from=awx-source /awx-src/requirements/requirements_git.txt /tmp/requirements/requirements_git.txt
COPY --from=awx-source /awx-src/requirements/requirements_dev.txt /tmp/requirements/requirements_dev.txt

WORKDIR /tmp
RUN --mount=type=ssh /usr/local/libexec/awx-docker/install-awx-python-deps

# ----- Final runtime image ----------------------------------------------------

FROM quay.io/centos/centos:stream9

ARG AWX_REPO
ARG AWX_REF
ARG AWX_REQUESTED_REF
ARG AWX_SOURCE_REVISION
ARG RECEPTOR_IMAGE
ARG INSTALL_PYTHON_DEBUGINFO=false

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8
ENV AWX_LOGGING_MODE=stdout
ENV HOME=/var/lib/awx
ENV PATH="/var/lib/awx/venv/awx/bin/:${PATH}"
ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.dev0+g${AWX_SOURCE_REVISION}"
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AWX="0.0.dev0+g${AWX_SOURCE_REVISION}"

LABEL org.opencontainers.image.title="Unofficial AWX proof-of-concept image"
LABEL org.opencontainers.image.description="AWX POC image built by cloning upstream AWX"
LABEL org.opencontainers.image.source="https://github.com/ansible/awx"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.vendor="unofficial"
LABEL dev.awx-wrapper.awx.repo="${AWX_REPO}"
LABEL dev.awx-wrapper.awx.requested-ref="${AWX_REQUESTED_REF}"
LABEL dev.awx-wrapper.awx.resolved-revision="${AWX_SOURCE_REVISION}"

USER root

# ----- Runtime OS packages ----------------------------------------------------

ADD https://copr.fedorainfracloud.org/coprs/ansible/Rsyslog/repo/epel-9/ansible-Rsyslog-epel-9.repo /etc/yum.repos.d/ansible-Rsyslog-epel-9.repo

COPY docker/awx/bin/install-rpms /usr/local/libexec/awx-docker/install-rpms
COPY docker/awx/bin/synthesize-awx-dist-info /usr/local/libexec/awx-docker/synthesize-awx-dist-info
COPY docker/awx/bin/prepare-runtime-layout /usr/local/libexec/awx-docker/prepare-runtime-layout
COPY docker/awx/bin/verify-runtime-contract /usr/local/libexec/awx-docker/verify-runtime-contract
COPY docker/awx/packages/runtime.rpms /tmp/packages.rpms
RUN INSTALL_RPMS_ENABLE_NODEJS18=true INSTALL_RPMS_INSTALL_INOTIFY=true \
    /usr/local/libexec/awx-docker/install-rpms /tmp/packages.rpms

# ----- Runtime Python tools ---------------------------------------------------

RUN pip3.12 install -vv --no-cache-dir virtualenv supervisor dumb-init build
RUN pip3.12 install -vv --no-cache-dir git+https://github.com/coderanger/supervisor-stdout.git@973ba19967cdaf46d9c1634d1675fc65b9574f6e
RUN pip3.12 install -vv --no-cache-dir black setuptools-scm
RUN if [ "$INSTALL_PYTHON_DEBUGINFO" = "true" ]; then \
      dnf --enablerepo=baseos-debug -y install python3-debuginfo && dnf -y clean all; \
    fi
RUN rm -rf /root/.cache && rm -rf /tmp/*

# ----- AWX source and launcher files -----------------------------------------

# Upstream AWX development launcher scripts expect a mounted checkout. This
# wrapper bakes the cloned source into the image, then removes Git metadata.
COPY --from=builder /var/lib/awx /var/lib/awx
COPY --from=ui-builder /tmp/src /awx_devel
COPY --from=receptor /usr/bin/receptor /usr/bin/receptor
RUN rm -rf /awx_devel/.git

RUN mkdir -p /usr/share/licenses/awx-wrapper && \
    cp /awx_devel/LICENSE.md /usr/share/licenses/awx-wrapper/AWX-LICENSE.md && \
    cp /awx_devel/.awx_source_revision /usr/share/licenses/awx-wrapper/AWX-SOURCE-REVISION && \
    cp /awx_devel/.awx_requested_ref /usr/share/licenses/awx-wrapper/AWX-REQUESTED-REF

RUN ln -s /var/lib/awx/venv/awx/bin/awx-manage /usr/bin/awx-manage

RUN openssl req -nodes -newkey rsa:2048 -keyout /etc/nginx/nginx.key -out /etc/nginx/nginx.csr \
        -subj "/C=US/ST=North Carolina/L=Durham/O=Ansible/OU=AWX Development/CN=awx.localhost" && \
    openssl x509 -req -days 365 -in /etc/nginx/nginx.csr -signkey /etc/nginx/nginx.key -out /etc/nginx/nginx.crt && \
    chmod 640 /etc/nginx/nginx.csr /etc/nginx/nginx.key /etc/nginx/nginx.crt

RUN rpm --restore shadow-utils 2>/dev/null || :
RUN sed -i -e 's|^#mount_program|mount_program|g' -e '/additionalimage.*/a "/var/lib/shared",' -e 's|^mountopt[[:space:]]*=.*$|mountopt = "nodev,fsync=0"|g' /etc/containers/storage.conf
ENV _CONTAINERS_USERNS_CONFIGURED=""
RUN mkdir -p /etc/containers/registries.conf.d/ && \
    echo "unqualified-search-registries = []" >> /etc/containers/registries.conf.d/force-fully-qualified-images.conf && \
    chmod 644 /etc/containers/registries.conf.d/force-fully-qualified-images.conf

COPY --from=awx-source /awx-src/tools/ansible/roles/dockerfile/files/rsyslog.conf /var/lib/awx/rsyslog/rsyslog.conf

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

# AWX's development launcher expects editable-package metadata from the mounted
# checkout. The helper synthesizes only that runtime metadata after the source
# is baked in and upstream Git data has been stripped.
RUN /usr/local/libexec/awx-docker/synthesize-awx-dist-info "${AWX_SOURCE_REVISION}"
RUN /usr/local/libexec/awx-docker/prepare-runtime-layout

WORKDIR /awx_devel

# ----- Network and startup ----------------------------------------------------

# 8043/8013 are nginx listeners for AWX HTTPS and websocket traffic. 8080/22
# remain exposed for compatibility with upstream AWX development tooling.
EXPOSE 8043 8013 8080 22

ENTRYPOINT ["/usr/local/bin/awx-wrapper-entrypoint"]
CMD ["/usr/bin/launch_awx.sh", "supervisord", "--pidfile=/tmp/supervisor_pid", "-n"]
