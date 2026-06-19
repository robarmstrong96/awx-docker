#!/usr/bin/env bash
set -euo pipefail

exec uv run awx-docker upstream-health "$@"
