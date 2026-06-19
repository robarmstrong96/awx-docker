#!/usr/bin/env bash
set -euo pipefail

cmd="${1:-help}"
if [[ $# -gt 0 ]]; then
	shift
fi

awx_ref="${AWX_REF:-devel}"
image_name="${IMAGE_NAME:-awx-devel}"
image_tag="${IMAGE_TAG:-devel}"

case "$cmd" in
doctor)
	command -v uv >/dev/null
	command -v dagger >/dev/null
	command -v git >/dev/null
	printf 'doctor: ok\n'
	;;
preflight | check)
	exec dagger call check --source=. "$@"
	;;
resolve-ref)
	exec uv run awx-docker resolve-ref --awx-ref="$awx_ref" "$@"
	;;
write-metadata)
	exec uv run awx-docker write-metadata --awx-ref="$awx_ref" "$@"
	;;
build)
	exec dagger call image-build \
		--source=. \
		--awx-ref="$awx_ref" \
		--image-name="$image_name" \
		--image-tag="$image_tag" \
		"$@"
	;;
verify-image)
	exec dagger call image-verify \
		--source=. \
		--awx-ref="$awx_ref" \
		--image-name="$image_name" \
		--image-tag="$image_tag" \
		"$@"
	;;
release-check)
	exec dagger call release-check --source=. --awx-ref="$awx_ref" "$@"
	;;
evidence)
	exec dagger call evidence --source=. "$@"
	;;
print-tags)
	printf '%s:%s\n' "$image_name" "$image_tag"
	;;
help | -h | --help | "")
	exec dagger functions
	;;
*)
	printf 'unknown image command: %s\n' "$cmd" >&2
	exec dagger functions
	;;
esac
