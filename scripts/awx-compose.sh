#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
fi

AWX_UPSTREAM_URL="${AWX_UPSTREAM_URL:-https://github.com/ansible/awx.git}"
AWX_BRANCH="${AWX_BRANCH:-devel}"
AWX_DIR="${AWX_DIR:-upstream/awx}"
COMPOSE_TAG="${COMPOSE_TAG:-devel}"
RECEPTOR_IMAGE="${RECEPTOR_IMAGE:-quay.io/ansible/receptor:devel}"
CONTROL_PLANE_NODE_COUNT="${CONTROL_PLANE_NODE_COUNT:-1}"
EXECUTION_NODE_COUNT="${EXECUTION_NODE_COUNT:-0}"

AWX_PATH="$AWX_DIR"
if [[ "$AWX_PATH" != /* ]]; then
  AWX_PATH="$ROOT_DIR/$AWX_PATH"
fi

COMPOSE_FILE="$AWX_PATH/tools/docker-compose/_sources/docker-compose.yml"

usage() {
  cat <<'USAGE'
Usage: scripts/awx-compose.sh <command>

Commands:
  doctor            Check host dependencies
  bootstrap         Clone upstream AWX devel if needed
  update            Fast-forward the upstream AWX checkout
  render            Render AWX compose/config sources
  build             Build awx_devel from the upstream checkout
  up                Start AWX detached by default
  up-build          Build awx_devel, then start AWX
  down              Stop AWX containers
  logs              Follow AWX compose logs
  ps                Show AWX compose services
  admin-password    Print generated admin password
  compose ...       Pass arguments to docker compose -f generated compose file
  clean-containers  Remove stopped AWX compose containers
  clean-volumes     Remove AWX containers and named volumes; requires CONFIRM=delete-awx-volumes
USAGE
}

require_cmd() {
  local missing=0
  for cmd in "$@"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      printf 'missing required command: %s\n' "$cmd" >&2
      missing=1
    fi
  done
  return "$missing"
}

require_docker() {
  require_cmd docker
  docker compose version >/dev/null
}

doctor() {
  local failed=0
  require_cmd git make ansible-playbook ansible-galaxy openssl || failed=1

  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    printf 'docker compose: ok\n'
  else
    printf 'docker compose: missing or unavailable; start/build commands will not work\n' >&2
    failed=1
  fi

  if [[ "$failed" -eq 0 ]]; then
    printf 'doctor: ok\n'
  else
    printf 'doctor: failed\n' >&2
    return 1
  fi
}

ensure_awx_checkout() {
  if [[ ! -d "$AWX_PATH/.git" ]]; then
    bootstrap
  fi
}

ensure_clean_awx_checkout() {
  ensure_awx_checkout
  if [[ -n "$(git -C "$AWX_PATH" status --porcelain)" ]]; then
    printf 'upstream checkout has local changes; refusing to update: %s\n' "$AWX_PATH" >&2
    return 1
  fi
}

bootstrap() {
  mkdir -p "$(dirname "$AWX_PATH")"

  if [[ -e "$AWX_PATH" && ! -d "$AWX_PATH/.git" ]]; then
    printf 'path exists but is not a git checkout: %s\n' "$AWX_PATH" >&2
    return 1
  fi

  if [[ ! -d "$AWX_PATH/.git" ]]; then
    git clone --depth 1 --branch "$AWX_BRANCH" "$AWX_UPSTREAM_URL" "$AWX_PATH"
  else
    update
  fi
}

update() {
  ensure_clean_awx_checkout
  git -C "$AWX_PATH" fetch --depth 1 origin "$AWX_BRANCH"
  git -C "$AWX_PATH" checkout "$AWX_BRANCH"
  git -C "$AWX_PATH" pull --ff-only origin "$AWX_BRANCH"
}

make_vars() {
  local vars=(
    "COMPOSE_TAG=$COMPOSE_TAG"
    "RECEPTOR_IMAGE=$RECEPTOR_IMAGE"
    "CONTROL_PLANE_NODE_COUNT=$CONTROL_PLANE_NODE_COUNT"
    "EXECUTION_NODE_COUNT=$EXECUTION_NODE_COUNT"
  )

  local passthrough=(
    ADMIN_PASSWORD COMPOSE_UP_OPTS COMPOSE_OPTS PGBOUNCER PROMETHEUS GRAFANA
    VAULT VAULT_TLS OTEL LOKI SPLUNK EDITABLE_DEPENDENCIES PG_TLS
    DEV_DOCKER_OWNER DEV_DOCKER_TAG_BASE DEVEL_IMAGE_NAME DOCKER_CACHE
  )

  local name
  for name in "${passthrough[@]}"; do
    if [[ -n "${!name:-}" ]]; then
      vars+=("$name=${!name}")
    fi
  done

  printf '%s\n' "${vars[@]}"
}

awx_make() {
  local target="$1"
  shift || true
  ensure_awx_checkout
  mapfile -t vars < <(make_vars)
  make -C "$AWX_PATH" "$target" "${vars[@]}" "$@"
}

render() {
  awx_make docker-compose-sources
}

build() {
  require_docker
  awx_make docker-compose-build
}

up() {
  require_docker
  export COMPOSE_UP_OPTS="${COMPOSE_UP_OPTS--d}"
  awx_make docker-compose
}

up_build() {
  build
  up
}

need_compose_file() {
  if [[ ! -f "$COMPOSE_FILE" ]]; then
    printf 'generated compose file not found; run make render first: %s\n' "$COMPOSE_FILE" >&2
    return 1
  fi
}

compose_cmd() {
  require_docker
  need_compose_file
  docker compose -f "$COMPOSE_FILE" "$@"
}

admin_password() {
  local password_file="$AWX_PATH/tools/docker-compose/_sources/secrets/admin_password.yml"
  if [[ ! -f "$password_file" ]]; then
    printf 'admin password file not found; run make render or make up first\n' >&2
    return 1
  fi
  awk -F"'" '/^admin_password:/{print $2}' "$password_file"
}

clean_volumes() {
  if [[ "${CONFIRM:-}" != "delete-awx-volumes" ]]; then
    printf 'refusing volume deletion; rerun with CONFIRM=delete-awx-volumes\n' >&2
    return 2
  fi
  require_docker
  awx_make docker-clean-volumes
}

cmd="${1:-}"
shift || true

case "$cmd" in
  doctor) doctor ;;
  bootstrap) bootstrap ;;
  update) update ;;
  render) render ;;
  build) build ;;
  up) up ;;
  up-build) up_build ;;
  down) awx_make docker-compose-down ;;
  logs) compose_cmd logs --tail="${TAIL:-200}" -f "$@" ;;
  ps) compose_cmd ps "$@" ;;
  admin-password) admin_password ;;
  compose) compose_cmd "$@" ;;
  clean-containers) awx_make docker-compose-clean ;;
  clean-volumes) clean_volumes ;;
  ""|help|-h|--help) usage ;;
  *)
    usage >&2
    exit 2
    ;;
esac
