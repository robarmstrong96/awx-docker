#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

pattern='/home/|\.cache/awx-docker|AWX_DIR|upstream/awx'

if rg -n --hidden \
  --glob '!.git/**' \
  --glob '!build/**' \
  --glob '!scripts/check-public-hygiene.sh' \
  "$pattern" "$ROOT_DIR"; then
  printf 'public hygiene check failed: remove local deployment references from public repo files\n' >&2
  exit 1
fi

printf 'public-hygiene: ok\n'
