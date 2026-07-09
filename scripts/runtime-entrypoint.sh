#!/usr/bin/env bash
#
# Prepare container-local AWX runtime configuration, repair runtime-only Podman
# state, and then hand off to the upstream AWX startup command.
set -euo pipefail

#######################################
# Check that required environment variables are set and non-empty.
# Globals:
#   None
# Arguments:
#   Environment variable names to check.
# Outputs:
#   Writes one error line to stderr for each missing variable.
# Returns:
#   0 when every named variable is present, 1 otherwise.
#######################################
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

#######################################
# Update user and group files for the runtime UID.
# Globals:
#   CURRENT_UID
# Arguments:
#   None
# Outputs:
#   Writes /etc/passwd, /etc/group, /etc/subuid, and /etc/subgid.
# Returns:
#   0 on success, non-zero on write failure.
#######################################
write_dynamic_users() {
	if [[ "$(id -u)" -lt 500 && -n "${CURRENT_UID:-}" ]]; then
		return
	fi

	local awx_uid awx_gid nginx_uid nginx_gid
	awx_uid="$(id -u)"
	awx_gid="$(id -g)"
	nginx_uid="$(id -u nginx 2>/dev/null || printf '999')"
	nginx_gid="$(id -g nginx 2>/dev/null || printf '999')"

	{
		printf 'root:x:0:0:root:/root:/bin/bash\n'
		printf 'awx:x:%s:%s:,,,:/var/lib/awx:/bin/bash\n' "$awx_uid" "$awx_gid"
		printf 'nginx:x:%s:%s:Nginx web server:/var/lib/nginx:/sbin/nologin\n' \
			"$nginx_uid" \
			"$nginx_gid"
	} >/etc/passwd

	printf 'awx:x:%s:awx\n' "$awx_uid" >>/etc/group
	printf 'awx:100000:50001\n' >/etc/subuid
	printf 'awx:100000:50001\n' >/etc/subgid
}

#######################################
# Generate AWX config files from deployment environment variables.
# Globals:
#   AWX_BROKER_URL
#   AWX_BROADCAST_WEBSOCKET_SECRET
#   AWX_CACHE_URL
#   AWX_CSRF_TRUSTED_ORIGIN
#   AWX_DB_HOST
#   AWX_DB_NAME
#   AWX_DB_PASSWORD
#   AWX_DB_PORT
#   AWX_DB_USER
#   AWX_SECRET_KEY
#   AWX_SYSTEM_UUID
# Arguments:
#   None
# Outputs:
#   Writes AWX configuration files under /etc/tower and /etc/receptor.
# Returns:
#   0 on success, non-zero when required configuration is missing.
#######################################
write_awx_config() {
	local config_src=/usr/local/share/awx-docker/tower

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
	install -m 0644 "$config_src/database.py" /etc/tower/conf.d/database.py
	install -m 0644 "$config_src/local_settings.py" /etc/tower/conf.d/local_settings.py
	install -m 0644 "$config_src/websocket_secret.py" /etc/tower/conf.d/websocket_secret.py

	printf '%s' "$AWX_SECRET_KEY" >/etc/tower/SECRET_KEY
	touch /etc/receptor/receptor.conf.lock
}

#######################################
# Clear container-local Podman runtime state from previous starts.
# Globals:
#   None
# Arguments:
#   None
# Outputs:
#   Removes runtime-only Podman state under /run and writes a stderr notice
#   when state was cleared.
# Returns:
#   0 on success, non-zero on remove failure.
#######################################
reset_podman_run_state() {
	local dir removed=0

	for dir in /run/containers/storage /run/libpod; do
		if [[ -e "$dir" ]]; then
			rm -rf -- "$dir"
			removed=1
		fi
	done

	if [[ "$removed" -eq 1 ]]; then
		printf 'cleared stale Podman runtime state under /run\n' >&2
	fi
}

write_dynamic_users
reset_podman_run_state
podman system migrate
export SDB_NOTIFY_HOST
SDB_NOTIFY_HOST="$(ip route | awk 'NR == 1 { print $3 }')"
write_awx_config

exec "$@"
