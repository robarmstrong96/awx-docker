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
EVIDENCE_DIR="${EVIDENCE_DIR:-$ROOT_DIR/build/evidence}"

mkdir -p "$EVIDENCE_DIR"

resolved_ref="$("$ROOT_DIR/scripts/image.sh" resolve-ref)"
repo_path="${AWX_REPO#https://github.com/}"
repo_path="${repo_path%.git}"

write_missing_signal() {
  local reason="$1"
  cat > "$EVIDENCE_DIR/upstream-status.env" <<EOF
AWX_REPO=$AWX_REPO
AWX_REQUESTED_REF=$AWX_REQUESTED_REF
AWX_RESOLVED_REF=$resolved_ref
UPSTREAM_STATUS_SIGNAL=missing
UPSTREAM_STATUS_DECISION=allowed
UPSTREAM_STATUS_REASON=$reason
EOF

  cat > "$EVIDENCE_DIR/upstream-status.md" <<EOF
# Upstream AWX Status

- AWX repo: \`$AWX_REPO\`
- AWX requested ref: \`$AWX_REQUESTED_REF\`
- AWX resolved ref: \`$resolved_ref\`
- Signal: missing
- Decision: allowed
- Reason: $reason
EOF
}

if [[ "$repo_path" == "$AWX_REPO" || -z "$repo_path" || "$repo_path" == */*/* ]]; then
  write_missing_signal "AWX_REPO is not a supported github.com/owner/repo URL, so upstream status could not be checked."
  printf 'upstream-status: allowed (unsupported repository URL)\n'
  exit 0
fi

api() {
  local url="$1"
  local -a headers=(
    -H "Accept: application/vnd.github+json"
    -H "X-GitHub-Api-Version: 2022-11-28"
  )

  if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    headers+=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
  fi

  curl -fsSL "${headers[@]}" "$url"
}

statuses_file="$EVIDENCE_DIR/upstream-combined-status.json"
checks_file="$EVIDENCE_DIR/upstream-check-runs.json"

if ! api "https://api.github.com/repos/${repo_path}/commits/${resolved_ref}/status" > "$statuses_file"; then
  write_missing_signal "GitHub combined status API request failed."
  printf 'upstream-status: allowed (status API unavailable)\n'
  exit 0
fi

if ! api "https://api.github.com/repos/${repo_path}/commits/${resolved_ref}/check-runs?per_page=100" > "$checks_file"; then
  write_missing_signal "GitHub check-runs API request failed."
  printf 'upstream-status: allowed (check-runs API unavailable)\n'
  exit 0
fi

if python3 - "$AWX_REPO" "$AWX_REQUESTED_REF" "$resolved_ref" "$EVIDENCE_DIR" "$statuses_file" "$checks_file" <<'PY'
import json
import pathlib
import sys

awx_repo, requested_ref, resolved_ref, evidence_dir, statuses_path, checks_path = sys.argv[1:]
evidence = pathlib.Path(evidence_dir)
statuses = json.loads(pathlib.Path(statuses_path).read_text())
checks = json.loads(pathlib.Path(checks_path).read_text())

status_contexts = statuses.get("statuses") or []
check_runs = checks.get("check_runs") or []
combined_state = statuses.get("state", "")
signal = "available" if status_contexts or check_runs else "missing"

fail_reasons = []
pending_reasons = []

if combined_state in {"failure", "error"}:
    fail_reasons.append(f"combined commit status is {combined_state}")
elif combined_state == "pending" and status_contexts:
    pending_reasons.append("combined commit status is pending")

bad_conclusions = {"failure", "cancelled", "timed_out", "action_required", "startup_failure"}
incomplete_statuses = {"queued", "in_progress", "pending", "requested", "waiting"}

for run in check_runs:
    name = run.get("name") or "unnamed check"
    status = run.get("status")
    conclusion = run.get("conclusion")
    if status in incomplete_statuses:
        pending_reasons.append(f"check run {name!r} is {status}")
    if conclusion in bad_conclusions:
        fail_reasons.append(f"check run {name!r} concluded {conclusion}")

if fail_reasons:
    decision = "blocked"
    reason = "; ".join(fail_reasons)
elif pending_reasons:
    decision = "blocked"
    reason = "; ".join(pending_reasons)
elif signal == "missing":
    decision = "allowed"
    reason = "GitHub exposed no combined status contexts or check runs for this upstream commit."
else:
    decision = "allowed"
    reason = "No failing or incomplete upstream statuses/check runs were found."

env_lines = [
    f"AWX_REPO={awx_repo}",
    f"AWX_REQUESTED_REF={requested_ref}",
    f"AWX_RESOLVED_REF={resolved_ref}",
    f"UPSTREAM_STATUS_SIGNAL={signal}",
    f"UPSTREAM_STATUS_DECISION={decision}",
    f"UPSTREAM_COMBINED_STATUS={combined_state or 'none'}",
    f"UPSTREAM_STATUS_CONTEXT_COUNT={len(status_contexts)}",
    f"UPSTREAM_CHECK_RUN_COUNT={len(check_runs)}",
    "UPSTREAM_STATUS_REASON=" + reason.replace("\n", " "),
]
(evidence / "upstream-status.env").write_text("\n".join(env_lines) + "\n")

md = [
    "# Upstream AWX Status",
    "",
    f"- AWX repo: `{awx_repo}`",
    f"- AWX requested ref: `{requested_ref}`",
    f"- AWX resolved ref: `{resolved_ref}`",
    f"- Signal: {signal}",
    f"- Combined status: `{combined_state or 'none'}`",
    f"- Status contexts: {len(status_contexts)}",
    f"- Check runs: {len(check_runs)}",
    f"- Decision: {decision}",
    f"- Reason: {reason}",
]
(evidence / "upstream-status.md").write_text("\n".join(md) + "\n")

if decision == "blocked":
    print(f"upstream-status: blocked ({reason})", file=sys.stderr)
    sys.exit(1)

print(f"upstream-status: allowed ({reason})")
PY
then
  exit 0
fi

exit 1
