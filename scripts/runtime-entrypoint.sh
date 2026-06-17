#!/usr/bin/env bash
set -euo pipefail

require_env() {
  local missing=0
  for name in "$@"; do
    if [[ -z "${!name:-}" ]]; then
      printf 'missing required environment variable: %s\n' "$name" >&2
      missing=1
    fi
  done
  return "$missing"
}

write_dynamic_users() {
  if [[ "$(id -u)" -lt 500 && -n "${CURRENT_UID:-}" ]]; then
    return
  fi

  local awx_uid awx_gid nginx_uid nginx_gid
  awx_uid="$(id -u)"
  awx_gid="$(id -g)"
  nginx_uid="$(id -u nginx 2>/dev/null || printf '999')"
  nginx_gid="$(id -g nginx 2>/dev/null || printf '999')"

  cat > /etc/passwd <<EOF
root:x:0:0:root:/root:/bin/bash
awx:x:${awx_uid}:${awx_gid}:,,,:/var/lib/awx:/bin/bash
nginx:x:${nginx_uid}:${nginx_gid}:Nginx web server:/var/lib/nginx:/sbin/nologin
EOF

  cat >> /etc/group <<EOF
awx:x:${awx_uid}:awx
EOF

  cat > /etc/subuid <<'EOF'
awx:100000:50001
EOF

  cat > /etc/subgid <<'EOF'
awx:100000:50001
EOF
}

write_awx_config() {
  require_env \
    AWX_BROKER_URL \
    AWX_BROADCAST_WEBSOCKET_SECRET \
    AWX_CACHE_URL \
    AWX_CSRF_TRUSTED_ORIGIN \
    AWX_DB_HOST \
    AWX_DB_NAME \
    AWX_DB_PASSWORD \
    AWX_DB_PORT \
    AWX_DB_USER \
    AWX_SECRET_KEY \
    AWX_SYSTEM_UUID

  install -d -m 0755 /etc/tower /etc/tower/conf.d /etc/receptor /etc/nginx/conf.d /var/run/redis

  cat > /etc/tower/conf.d/database.py <<'PY'
import os

DATABASES = {
    "default": {
        "ATOMIC_REQUESTS": True,
        "ENGINE": "awx.main.db.profiled_pg",
        "NAME": os.environ["AWX_DB_NAME"],
        "USER": os.environ["AWX_DB_USER"],
        "PASSWORD": os.environ["AWX_DB_PASSWORD"],
        "HOST": os.environ["AWX_DB_HOST"],
        "PORT": os.environ["AWX_DB_PORT"],
    }
}

if os.environ.get("AWX_DB_SSLMODE"):
    DATABASES["default"]["OPTIONS"] = {"sslmode": os.environ["AWX_DB_SSLMODE"]}
PY

  cat > /etc/tower/conf.d/local_settings.py <<'PY'
import os

SYSTEM_UUID = os.environ["AWX_SYSTEM_UUID"]

ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = [os.environ["AWX_CSRF_TRUSTED_ORIGIN"]]
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

BROKER_URL = os.environ["AWX_BROKER_URL"]
CACHES = {
    "default": {
        "BACKEND": "ansible_base.lib.cache.redis_cache.DABRedisCache",
        "LOCATION": os.environ["AWX_CACHE_URL"],
    }
}
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [BROKER_URL],
            "capacity": 10000,
            "group_expiry": 157784760,
        },
    }
}

BROADCAST_WEBSOCKET_PORT = 8013
BROADCAST_WEBSOCKET_VERIFY_CERT = False
BROADCAST_WEBSOCKET_PROTOCOL = "http"

STATIC_URL = "/static/"
PY

  cat > /etc/tower/conf.d/websocket_secret.py <<'PY'
import os

BROADCAST_WEBSOCKET_SECRET = os.environ["AWX_BROADCAST_WEBSOCKET_SECRET"]
PY

  cat > /etc/nginx/nginx.conf <<'NGINX'
worker_processes 1;

error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    server_tokens off;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    map $http_upgrade $connection_upgrade {
        default upgrade;
        '' close;
    }

    sendfile on;

    upstream uwsgi {
        server localhost:8050;
    }

    upstream runserver {
        server localhost:8052;
    }

    upstream daphne {
        server localhost:8051;
    }

    server {
        listen 8013 default_server;
        server_name _;
        keepalive_timeout 65;

        add_header Strict-Transport-Security max-age=15768000;
        add_header X-Content-Type-Options nosniff;

        include /etc/nginx/conf.d/*.conf;
    }

    server {
        listen 8043 default_server ssl;
        server_name _;
        keepalive_timeout 65;

        ssl_certificate /etc/nginx/nginx.crt;
        ssl_certificate_key /etc/nginx/nginx.key;
        ssl_session_timeout 1d;
        ssl_session_cache shared:SSL:50m;
        ssl_session_tickets off;
        ssl_protocols TLSv1.2;
        ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256';
        ssl_prefer_server_ciphers on;

        add_header Strict-Transport-Security max-age=15768000;
        add_header X-Content-Type-Options nosniff;

        include /etc/nginx/conf.d/*.conf;
    }
}
NGINX

  cat > /etc/nginx/conf.d/nginx.locations.conf <<'NGINX'
location /static {
    alias /var/lib/awx/public/static/;
}

location /locales {
    alias /var/lib/awx/public/static/awx/locales;
}

location /favicon.ico {
    alias /awx_devel/awx/public/static/favicon.ico;
}

location ~ ^(/websocket/|/api/websocket/) {
    proxy_pass http://daphne;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header Host $http_host;
    proxy_redirect off;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
}

location / {
    rewrite ^(.*)$http_host(.*[^/])$ $1$http_host$2/ permanent;
    uwsgi_read_timeout 120s;
    uwsgi_pass uwsgi;
    include /etc/nginx/uwsgi_params;
    error_page 502 = @fallback;
}

location @fallback {
    rewrite ^(.*)$http_host(.*[^/])$ $1$http_host$2/ permanent;
    proxy_pass http://runserver;
    proxy_set_header Host $http_host;
}
NGINX

  cat > /etc/receptor/receptor.conf <<'YAML'
---
- node:
    id: awx-1
    firewallrules:
      - action: reject
        tonode: awx-1
        toservice: control

- log-level: info

- tcp-listener:
    port: 2222

- control-service:
    service: control
    filename: /var/run/awx-receptor/receptor.sock

- work-command:
    worktype: local
    command: ansible-runner
    params: worker
    allowruntimeparams: true
    verifysignature: false

- work-kubernetes:
    worktype: kubernetes-runtime-auth
    authmethod: runtime
    allowruntimeauth: true
    allowruntimepod: true
    allowruntimeparams: true
    verifysignature: false

- work-kubernetes:
    worktype: kubernetes-incluster-auth
    authmethod: incluster
    allowruntimeauth: true
    allowruntimepod: true
    allowruntimeparams: true
    verifysignature: false
YAML

  printf '%s' "$AWX_SECRET_KEY" > /etc/tower/SECRET_KEY
  touch /etc/receptor/receptor.conf.lock
}

write_dynamic_users
podman system migrate
export SDB_NOTIFY_HOST
SDB_NOTIFY_HOST="$(ip route | awk 'NR == 1 { print $3 }')"
write_awx_config

exec "$@"
