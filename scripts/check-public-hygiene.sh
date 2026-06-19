#!/usr/bin/env bash
set -euo pipefail

exec uv run awx-docker public-hygiene "$@"
