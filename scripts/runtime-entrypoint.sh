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

  printf '%s' "$AWX_SECRET_KEY" > /etc/tower/SECRET_KEY
  touch /etc/receptor/receptor.conf.lock
}

write_dynamic_users
podman system migrate
export SDB_NOTIFY_HOST
SDB_NOTIFY_HOST="$(ip route | awk 'NR == 1 { print $3 }')"
write_awx_config

exec "$@"
