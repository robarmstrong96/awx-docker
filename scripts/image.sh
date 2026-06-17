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

AWX_REPO="${AWX_REPO:-https://github.com/ansible/awx.git}"
AWX_REF="${AWX_REF:-devel}"
RECEPTOR_IMAGE="${RECEPTOR_IMAGE:-quay.io/ansible/receptor:devel}"
IMAGE_NAME="${IMAGE_NAME:-awx-devel}"
IMAGE_TAG="${IMAGE_TAG:-${AWX_REF//\//-}}"
PLATFORM="${PLATFORM:-linux/amd64}"
PUSH="${PUSH:-false}"
DOCKERFILE="${DOCKERFILE:-$ROOT_DIR/Dockerfile}"

usage() {
  cat <<'USAGE'
Usage: scripts/image.sh <command>

Commands:
  doctor       Check local image-builder dependencies
  preflight    Run static checks that do not require Docker
  resolve-ref  Resolve AWX_REF to a concrete upstream commit SHA
  build        Build the AWX image locally
  push         Push the already-built image tag
  print-tags   Print the image reference that build/push uses
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

image_ref() {
  printf '%s:%s\n' "$IMAGE_NAME" "$IMAGE_TAG"
}

resolve_ref() {
  require_cmd git awk

  if [[ "$AWX_REF" =~ ^[0-9a-fA-F]{40}$ ]]; then
    printf '%s\n' "$AWX_REF"
    return
  fi

  local refs
  refs="$(git ls-remote "$AWX_REPO" \
    "$AWX_REF" \
    "refs/heads/$AWX_REF" \
    "refs/tags/$AWX_REF" \
    "refs/tags/$AWX_REF^{}")"

  if [[ -z "$refs" ]]; then
    printf 'unable to resolve AWX_REF=%s from %s\n' "$AWX_REF" "$AWX_REPO" >&2
    return 1
  fi

  awk '
    $2 ~ /\^\{\}$/ { peeled=$1 }
    $2 ~ /^refs\/heads\// { head=$1 }
    $2 ~ /^refs\/tags\// && $2 !~ /\^\{\}$/ { tag=$1 }
    NR == 1 { first=$1 }
    END {
      if (peeled) print peeled;
      else if (head) print head;
      else if (tag) print tag;
      else print first;
    }
  ' <<<"$refs"
}

doctor() {
  local failed=0
  require_cmd git awk sed || failed=1
  if command -v docker >/dev/null 2>&1; then
    docker version >/dev/null || failed=1
    docker buildx version >/dev/null || failed=1
  else
    printf 'missing required command: docker\n' >&2
    failed=1
  fi

  if [[ "$failed" -eq 0 ]]; then
    printf 'doctor: ok\n'
  else
    printf 'doctor: failed\n' >&2
    return 1
  fi
}

preflight() {
  require_cmd awk sed git
  local fetch_pattern="git -C /awx-src fetch --depth 1 origin \"\${AWX_REF}\""
  local source_copy_pattern='COPY --from=ui-builder /tmp/src /awx_devel'

  test -f "$DOCKERFILE"
  grep -Fq "$fetch_pattern" "$DOCKERFILE"
  grep -Fq "$source_copy_pattern" "$DOCKERFILE"

  if find "$ROOT_DIR" -path "$ROOT_DIR/.git" -prune -o -name .git -type d -print | grep -q .; then
    printf 'nested git checkout found under repo; image builds must clone AWX at Docker build time\n' >&2
    return 1
  fi

  printf 'preflight: ok\n'
}

docker_build_args() {
  local resolved_ref="$1"
  local args=(
    buildx
    build
    --file "$DOCKERFILE"
    --platform "$PLATFORM"
    --build-arg "AWX_REPO=$AWX_REPO"
    --build-arg "AWX_REF=$resolved_ref"
    --build-arg "AWX_REQUESTED_REF=$AWX_REF"
    --build-arg "AWX_SOURCE_REVISION=$resolved_ref"
    --build-arg "RECEPTOR_IMAGE=$RECEPTOR_IMAGE"
    --label "org.opencontainers.image.revision=$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || echo unknown)"
    --label "dev.awx-wrapper.awx.repo=$AWX_REPO"
    --label "dev.awx-wrapper.awx.ref=$AWX_REF"
    --label "dev.awx-wrapper.awx.revision=$resolved_ref"
    --tag "$(image_ref)"
  )

  if [[ -n "${SSH_AUTH_SOCK:-}" ]]; then
    args+=(--ssh "default=$SSH_AUTH_SOCK")
  fi

  if [[ "$PUSH" == "true" ]]; then
    args+=(--push)
  else
    args+=(--load)
  fi

  args+=("$ROOT_DIR")
  printf '%s\0' "${args[@]}"
}

build_image() {
  preflight
  doctor
  local resolved_ref
  resolved_ref="$(resolve_ref)"
  printf 'resolved %s to %s\n' "$AWX_REF" "$resolved_ref"
  export DOCKER_BUILDKIT=1
  local -a args
  mapfile -d '' -t args < <(docker_build_args "$resolved_ref")
  docker "${args[@]}"
}

push_image() {
  doctor
  docker push "$(image_ref)"
}

cmd="${1:-}"
shift || true

case "$cmd" in
  doctor) doctor ;;
  preflight) preflight ;;
  resolve-ref) resolve_ref ;;
  build) build_image ;;
  push) push_image ;;
  print-tags) image_ref ;;
  ""|help|-h|--help) usage ;;
  *)
    usage >&2
    exit 2
    ;;
esac
