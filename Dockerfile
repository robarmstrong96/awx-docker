# syntax=docker/dockerfile:1.7

ARG AWX_REPO=https://github.com/ansible/awx.git
ARG AWX_REF=devel
ARG AWX_REQUESTED_REF=devel
ARG AWX_SOURCE_REVISION=unknown
ARG RECEPTOR_IMAGE=quay.io/ansible/receptor:devel

FROM ${RECEPTOR_IMAGE} AS receptor

FROM quay.io/centos/centos:stream9 AS awx-source
ARG AWX_REPO
ARG AWX_REF
ARG AWX_REQUESTED_REF

RUN dnf -y update && \
    dnf -y install ca-certificates git-core && \
    dnf -y clean all

RUN git init /awx-src && \
    git -C /awx-src remote add origin "${AWX_REPO}" && \
    git -C /awx-src fetch --depth 1 origin "${AWX_REF}" && \
    git -C /awx-src checkout --detach FETCH_HEAD && \
    git -C /awx-src rev-parse HEAD > /awx-src/.awx_source_revision && \
    printf '%s\n' "${AWX_REQUESTED_REF}" > /awx-src/.awx_requested_ref

FROM quay.io/centos/centos:stream9 AS ui-builder

USER root
RUN dnf -y update && \
    dnf module -y enable nodejs:18 && \
    dnf module -y install nodejs:18/common && \
    dnf -y install git-core make && \
    dnf -y clean all

COPY --from=awx-source /awx-src /tmp/src
WORKDIR /tmp/src
RUN make ui

FROM quay.io/centos/centos:stream9 AS builder

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8
ENV AWX_LOGGING_MODE=stdout

USER root

RUN rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-centosofficial

RUN dnf -y update && dnf install -y 'dnf-command(config-manager)' && \
    dnf config-manager --set-enabled crb && \
    dnf -y install \
    openssh-clients \
    iputils \
    gcc \
    gcc-c++ \
    git-core \
    gettext \
    glibc-langpack-en \
    libffi-devel \
    libtool-ltdl-devel \
    make \
    nss \
    patch \
    postgresql \
    postgresql-devel \
    python3.12 \
    "python3.12-devel" \
    "python3.12-pip" \
    "python3.12-setuptools" \
    "python3.12-packaging" \
    "python3.12-psycopg2" \
    swig \
    unzip \
    xmlsec1-devel \
    xmlsec1-openssl-devel && \
    dnf -y clean all

RUN mkdir -p ~/.ssh && chmod 0700 ~/.ssh && ssh-keyscan github.com > ~/.ssh/known_hosts
RUN pip3.12 install -vv --no-cache-dir build

COPY --from=awx-source /awx-src/Makefile /tmp/Makefile
RUN mkdir /tmp/requirements
COPY --from=awx-source /awx-src/requirements/requirements.txt /tmp/requirements/requirements.txt
COPY --from=awx-source /awx-src/requirements/requirements_tower_uninstall.txt /tmp/requirements/requirements_tower_uninstall.txt
COPY --from=awx-source /awx-src/requirements/requirements_git.txt /tmp/requirements/requirements_git.txt

WORKDIR /tmp
RUN --mount=type=ssh make requirements_awx

ARG VERSION
ARG SETUPTOOLS_SCM_PRETEND_VERSION

COPY --from=awx-source /awx-src/requirements/requirements_dev.txt /tmp/requirements/requirements_dev.txt
RUN make requirements_awx_dev

FROM quay.io/centos/centos:stream9

ARG AWX_REPO
ARG AWX_REF
ARG AWX_REQUESTED_REF
ARG AWX_SOURCE_REVISION
ARG RECEPTOR_IMAGE

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8
ENV AWX_LOGGING_MODE=stdout
ENV HOME=/var/lib/awx
ENV PATH="/var/lib/awx/venv/awx/bin/:${PATH}"

LABEL org.opencontainers.image.title="Unofficial AWX development image"
LABEL org.opencontainers.image.description="AWX image built by cloning upstream AWX during Docker build"
LABEL org.opencontainers.image.source="https://github.com/ansible/awx"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.vendor="unofficial"
LABEL dev.awx-wrapper.awx.repo="${AWX_REPO}"
LABEL dev.awx-wrapper.awx.requested-ref="${AWX_REQUESTED_REF}"
LABEL dev.awx-wrapper.awx.resolved-revision="${AWX_SOURCE_REVISION}"

USER root

RUN rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-centosofficial

ADD https://copr.fedorainfracloud.org/coprs/ansible/Rsyslog/repo/epel-9/ansible-Rsyslog-epel-9.repo /etc/yum.repos.d/ansible-Rsyslog-epel-9.repo

RUN dnf -y update && dnf install -y 'dnf-command(config-manager)' && \
    dnf config-manager --set-enabled crb && \
    dnf -y install acl \
    git-core \
    git-lfs \
    glibc-langpack-en \
    krb5-workstation \
    nginx \
    postgresql \
    python3.12 \
    "python3.12-devel" \
    "python3.12-pip*" \
    "python3.12-setuptools" \
    "python3.12-packaging" \
    "python3.12-psycopg2" \
    rsync \
    rsyslog \
    subversion \
    sudo \
    vim-minimal \
    which \
    unzip \
    xmlsec1-openssl && \
    dnf -y clean all

RUN pip3.12 install -vv --no-cache-dir virtualenv supervisor dumb-init build
RUN rm -rf /root/.cache && rm -rf /tmp/*

RUN dnf module -y enable nodejs:18 && dnf module -y install nodejs:18/common && \
    dnf -y install \
    crun \
    gdb \
    gtk3 \
    gettext \
    hostname \
    procps \
    alsa-lib \
    libX11-xcb \
    libXScrnSaver \
    iproute \
    strace \
    vim \
    nmap-ncat \
    libpq-devel \
    nss \
    make \
    patch \
    socat \
    tmux \
    wget \
    diffutils \
    unzip && \
    dnf -y clean all

RUN pip3.12 install -vv --no-cache-dir git+https://github.com/coderanger/supervisor-stdout.git@973ba19967cdaf46d9c1634d1675fc65b9574f6e
RUN pip3.12 install -vv --no-cache-dir black setuptools-scm build
RUN (dnf --enablerepo=baseos-debug -y install python3-debuginfo && dnf -y clean all) || :
RUN dnf install -y epel-next-release && dnf install -y inotify-tools && dnf remove -y epel-next-release && dnf -y clean all

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

RUN dnf install -y podman && rpm --restore shadow-utils 2>/dev/null && dnf -y clean all
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

RUN echo /awx_devel > /var/lib/awx/venv/awx/lib/python3.12/site-packages/awx.egg-link && \
    echo /awx_devel > /var/lib/awx/venv/awx/lib/python3.12/site-packages/awx.pth && \
    ln -sf /awx_devel/tools/docker-compose/awx-manage /usr/local/bin/awx-manage && \
    ln -sf /awx_devel/tools/scripts/awx-python /usr/bin/awx-python && \
    ln -sf /awx_devel/tools/scripts/rsyslog-4xx-recovery /usr/bin/rsyslog-4xx-recovery

RUN for dir in \
      /var/lib/awx \
      /var/lib/awx/rsyslog \
      /var/lib/awx/rsyslog/conf.d \
      /var/lib/awx/.local/share/containers/storage \
      /var/run/awx-rsyslog \
      /var/log/nginx \
      /var/lib/pgsql \
      /var/run/supervisor \
      /var/run/awx-receptor \
      /var/lib/nginx ; \
    do install -d -m 0775 -g root "$dir" ; chmod g+rwx "$dir" ; done && \
    for file in \
      /etc/subuid \
      /etc/subgid \
      /etc/group \
      /etc/passwd \
      /var/lib/awx/rsyslog/rsyslog.conf ; \
    do touch "$file" ; chmod g+rw "$file" ; chgrp root "$file" ; done

RUN for dir in \
      /var/lib/awx/.local \
      /var/lib/awx/venv \
      /var/lib/awx/venv/awx/bin \
      /var/lib/awx/venv/awx/lib/python3.12 \
      /var/lib/awx/venv/awx/lib/python3.12/site-packages \
      /var/lib/awx/projects \
      /var/lib/awx/rsyslog \
      /var/run/awx-rsyslog \
      /.ansible \
      /var/lib/shared/overlay-images \
      /var/lib/shared/overlay-layers \
      /var/lib/shared/vfs-images \
      /var/lib/shared/vfs-layers \
      /var/lib/awx/vendor ; \
    do install -d -m 0775 -g root "$dir" ; chmod g+rwx "$dir" ; done && \
    for file in \
      /var/lib/shared/overlay-images/images.lock \
      /var/lib/shared/overlay-layers/layers.lock \
      /var/lib/shared/vfs-images/images.lock \
      /var/lib/shared/vfs-layers/layers.lock \
      /var/run/nginx.pid; \
    do touch "$file" ; chmod g+rw "$file" ; done && \
    echo "\setenv PAGER 'less -SXF'" > /var/lib/awx/.psqlrc

WORKDIR /awx_devel

EXPOSE 8043 8013 8080 22

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/bin/bash"]
