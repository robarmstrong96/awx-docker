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
AWX_REQUESTED_REF="${AWX_REQUESTED_REF:-$AWX_REF}"
AWX_RESOLVED_REF="${AWX_RESOLVED_REF:-}"
RECEPTOR_IMAGE="${RECEPTOR_IMAGE:-quay.io/ansible/receptor:devel}"
IMAGE_NAME="${IMAGE_NAME:-awx-devel}"
IMAGE_TAG="${IMAGE_TAG:-${AWX_REF//\//-}}"
PLATFORM="${PLATFORM:-linux/amd64}"
DOCKERFILE="${DOCKERFILE:-$ROOT_DIR/Dockerfile}"
EVIDENCE_DIR="${EVIDENCE_DIR:-$ROOT_DIR/build/evidence}"

usage() {
  cat <<'USAGE'
Usage: scripts/image.sh <command>

Commands:
  doctor       Check local image-builder dependencies
  preflight    Run static checks that do not require Docker
  resolve-ref  Resolve AWX_REF to a concrete upstream commit SHA
  write-metadata Write build metadata evidence without Docker
  write-runner-diagnostics Write Docker runner diagnostics evidence
  build        Build the AWX image locally
  verify-image Verify the built image contents and metadata
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

wrapper_revision() {
  git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || echo unknown
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

write_metadata() {
  require_cmd git awk
  local resolved_ref
  if [[ -n "$AWX_RESOLVED_REF" ]]; then
    resolved_ref="$AWX_RESOLVED_REF"
  else
    resolved_ref="$(resolve_ref)"
  fi
  local wrapper_ref
  wrapper_ref="$(wrapper_revision)"
  local ref
  ref="$(image_ref)"

  mkdir -p "$EVIDENCE_DIR"
  cat > "$EVIDENCE_DIR/build-metadata.env" <<EOF
IMAGE_REF=$ref
IMAGE_NAME=$IMAGE_NAME
IMAGE_TAG=$IMAGE_TAG
AWX_REPO=$AWX_REPO
AWX_REQUESTED_REF=$AWX_REQUESTED_REF
AWX_RESOLVED_REF=$resolved_ref
WRAPPER_REVISION=$wrapper_ref
PLATFORM=$PLATFORM
EOF

  cat > "$EVIDENCE_DIR/build-metadata.md" <<EOF
# AWX Image Build Metadata

- Image: \`$ref\`
- AWX repo: \`$AWX_REPO\`
- AWX requested ref: \`$AWX_REQUESTED_REF\`
- AWX resolved ref: \`$resolved_ref\`
- Wrapper revision: \`$wrapper_ref\`
- Platform: \`$PLATFORM\`
EOF

  printf '%s\n' "$EVIDENCE_DIR/build-metadata.env"
}

write_runner_diagnostics() {
  require_cmd awk df uname

  local docker_cli=missing
  local docker_cli_version=unavailable
  local docker_server_version=unavailable
  local buildx_version=unavailable
  local buildx_details=unavailable

  if command -v docker >/dev/null 2>&1; then
    docker_cli=available
    docker_cli_version="$(docker version --format '{{.Client.Version}}' 2>/dev/null || printf 'unavailable')"
    docker_server_version="$(docker version --format '{{.Server.Version}}' 2>/dev/null || printf 'unavailable')"
    buildx_details="$(docker buildx version 2>/dev/null || printf 'unavailable')"
    buildx_version="$(awk '{ print $2 }' <<<"$buildx_details")"
    if [[ -z "$buildx_version" ]]; then
      buildx_version=unavailable
    fi
  fi

  local kernel_name kernel_release kernel_machine
  kernel_name="$(uname -s)"
  kernel_release="$(uname -r)"
  kernel_machine="$(uname -m)"
  local root_disk root_total_kib root_available_kib root_used_percent
  root_disk="$(df -h / | awk 'NR == 2 { print $2 " total, " $4 " available, " $5 " used" }')"
  root_total_kib="$(df -Pk / | awk 'NR == 2 { print $2 }')"
  root_available_kib="$(df -Pk / | awk 'NR == 2 { print $4 }')"
  root_used_percent="$(df -Pk / | awk 'NR == 2 { print $5 }')"

  mkdir -p "$EVIDENCE_DIR"
  cat > "$EVIDENCE_DIR/runner-diagnostics.env" <<EOF
RUNNER_OS=${RUNNER_OS:-unknown}
RUNNER_ARCH=${RUNNER_ARCH:-unknown}
KERNEL_NAME=$kernel_name
KERNEL_RELEASE=$kernel_release
KERNEL_MACHINE=$kernel_machine
ROOT_DISK_TOTAL_KIB=$root_total_kib
ROOT_DISK_AVAILABLE_KIB=$root_available_kib
ROOT_DISK_USED_PERCENT=$root_used_percent
DOCKER_CLI=$docker_cli
DOCKER_CLI_VERSION=$docker_cli_version
DOCKER_SERVER_VERSION=$docker_server_version
DOCKER_BUILDX_VERSION=$buildx_version
EOF

  cat > "$EVIDENCE_DIR/runner-diagnostics.md" <<EOF
# Runner Diagnostics

- Runner OS: \`${RUNNER_OS:-unknown}\`
- Runner arch: \`${RUNNER_ARCH:-unknown}\`
- Kernel: \`$kernel_name $kernel_release $kernel_machine\`
- Root disk: \`$root_disk\`
- Docker CLI: \`$docker_cli_version\`
- Docker server: \`$docker_server_version\`
- Docker Buildx: \`$buildx_details\`
EOF

  printf '%s\n' "$EVIDENCE_DIR/runner-diagnostics.env"
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
  local strip_git_pattern='RUN rm -rf /awx_devel/.git'

  test -f "$DOCKERFILE"
  grep -Fq "$fetch_pattern" "$DOCKERFILE"
  grep -Fq "$source_copy_pattern" "$DOCKERFILE"
  grep -Fq "$strip_git_pattern" "$DOCKERFILE"

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
    --build-arg "AWX_REQUESTED_REF=$AWX_REQUESTED_REF"
    --build-arg "AWX_SOURCE_REVISION=$resolved_ref"
    --build-arg "RECEPTOR_IMAGE=$RECEPTOR_IMAGE"
    --label "org.opencontainers.image.revision=$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || echo unknown)"
    --label "dev.awx-wrapper.awx.repo=$AWX_REPO"
    --label "dev.awx-wrapper.awx.ref=$AWX_REQUESTED_REF"
    --label "dev.awx-wrapper.awx.revision=$resolved_ref"
    --tag "$(image_ref)"
  )

  if [[ -n "${SSH_AUTH_SOCK:-}" ]]; then
    args+=(--ssh "default=$SSH_AUTH_SOCK")
  fi

  args+=(--load)

  args+=("$ROOT_DIR")
  printf '%s\0' "${args[@]}"
}

build_image() {
  preflight
  doctor
  local resolved_ref
  resolved_ref="$(resolve_ref)"
  printf 'resolved %s to %s\n' "$AWX_REF" "$resolved_ref"
  AWX_RESOLVED_REF="$resolved_ref" write_metadata >/dev/null
  export DOCKER_BUILDKIT=1
  local -a args
  mapfile -d '' -t args < <(docker_build_args "$resolved_ref")
  docker "${args[@]}"
}

verify_image() {
  doctor
  local expected_ref
  expected_ref="$(resolve_ref)"
  local ref
  ref="$(image_ref)"

  docker image inspect "$ref" >/dev/null

  local label_revision
  label_revision="$(docker image inspect --format '{{ index .Config.Labels "dev.awx-wrapper.awx.revision" }}' "$ref")"
  if [[ "$label_revision" != "$expected_ref" ]]; then
    printf 'image label revision mismatch: expected %s, got %s\n' "$expected_ref" "$label_revision" >&2
    return 1
  fi

  local image_revision
  image_revision="$(
    docker run --rm --entrypoint /bin/bash "$ref" -lc '
      set -euo pipefail
      test -f /awx_devel/manage.py
      test -f /awx_devel/LICENSE.md
      test ! -e /awx_devel/.git
      test -x /entrypoint.sh
      test -f /etc/supervisord.conf
      test -x /usr/local/bin/awx-manage
      test -f /usr/share/licenses/awx-wrapper/AWX-LICENSE.md
      test -f /usr/share/licenses/awx-wrapper/AWX-REQUESTED-REF
      cat /usr/share/licenses/awx-wrapper/AWX-SOURCE-REVISION
    '
  )"

  if [[ "$image_revision" != "$expected_ref" ]]; then
    printf 'image source revision mismatch: expected %s, got %s\n' "$expected_ref" "$image_revision" >&2
    return 1
  fi

  mkdir -p "$EVIDENCE_DIR"
  cat > "$EVIDENCE_DIR/image-verification.env" <<EOF
IMAGE_REF=$ref
AWX_EXPECTED_REF=$expected_ref
AWX_IMAGE_REF=$image_revision
AWX_LABEL_REF=$label_revision
AWX_GIT_METADATA=absent
VERIFICATION_STATUS=passed
EOF

  cat > "$EVIDENCE_DIR/image-verification.md" <<EOF
# AWX Image Verification

- Image: \`$ref\`
- Expected AWX revision: \`$expected_ref\`
- Image AWX revision: \`$image_revision\`
- Image label revision: \`$label_revision\`
- Embedded AWX git metadata: absent
- Status: passed
EOF

  printf 'verify-image: ok (%s contains AWX %s)\n' "$ref" "$expected_ref"
}

push_image() {
  verify_image
  docker push "$(image_ref)"
}

cmd="${1:-}"
shift || true

case "$cmd" in
  doctor) doctor ;;
  preflight) preflight ;;
  resolve-ref) resolve_ref ;;
  write-metadata) write_metadata ;;
  write-runner-diagnostics) write_runner_diagnostics ;;
  build) build_image ;;
  verify-image) verify_image ;;
  push) push_image ;;
  print-tags) image_ref ;;
  ""|help|-h|--help) usage ;;
  *)
    usage >&2
    exit 2
    ;;
esac
