from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from awx_docker.evidence import write_env, write_json, write_markdown

LOCK_SCHEMA_VERSION = "awx-docker.awx-lock/v1"
SHA_PATTERN_LENGTH = 40


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def is_sha(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == SHA_PATTERN_LENGTH
        and all(char in "0123456789abcdefABCDEF" for char in value)
    )


def image_ref(lock: Mapping[str, Any]) -> str:
    image = lock.get("image", {})
    return f"{image.get('name', '')}:{image.get('tag', '')}"


def load_lock(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping")
    return data


def build_lock(
    repository: str,
    requested_ref: str,
    resolved_revision: str,
    image_name: str,
    image_tag: str,
    *,
    observed_at: str | None = None,
    source_branch: str = "development",
    promoted_by: str = "",
    evidence_run_url: str = "",
    evidence_waiver: str = "",
    notes: str = "",
) -> dict[str, Any]:
    return {
        "schema": LOCK_SCHEMA_VERSION,
        "upstream": {
            "repository": repository,
            "requested_ref": requested_ref,
            "resolved_revision": resolved_revision,
            "observed_at": observed_at or utc_now(),
        },
        "image": {"name": image_name, "tag": image_tag},
        "promotion": {
            "source_branch": source_branch,
            "promoted_by": promoted_by,
            "evidence_run_url": evidence_run_url,
            "evidence_waiver": evidence_waiver,
            "notes": notes,
        },
    }


def write_lock(path: Path, lock: Mapping[str, Any]) -> None:
    path.write_text(yaml.safe_dump(dict(lock), sort_keys=False))


def validate_lock(
    lock: Mapping[str, Any],
    *,
    require_promotion_evidence: bool = False,
) -> list[str]:
    errors = []
    if lock.get("schema") != LOCK_SCHEMA_VERSION:
        errors.append(f"schema must be {LOCK_SCHEMA_VERSION}")

    upstream = lock.get("upstream")
    if not isinstance(upstream, Mapping):
        errors.append("upstream must be a mapping")
        upstream = {}
    image = lock.get("image")
    if not isinstance(image, Mapping):
        errors.append("image must be a mapping")
        image = {}
    promotion = lock.get("promotion")
    if not isinstance(promotion, Mapping):
        errors.append("promotion must be a mapping")
        promotion = {}

    for key in ("repository", "requested_ref", "observed_at"):
        if not upstream.get(key):
            errors.append(f"upstream.{key} is required")
    if not is_sha(upstream.get("resolved_revision")):
        errors.append("upstream.resolved_revision must be a 40-character git SHA")
    for key in ("name", "tag"):
        if not image.get(key):
            errors.append(f"image.{key} is required")
    if not promotion.get("source_branch"):
        errors.append("promotion.source_branch is required")
    if require_promotion_evidence:
        if not promotion.get("promoted_by"):
            errors.append("promotion.promoted_by is required for production admission")
        if not promotion.get("evidence_run_url") and not promotion.get("evidence_waiver"):
            errors.append(
                "promotion.evidence_run_url or promotion.evidence_waiver is required "
                "for production admission"
            )
    return errors


def branch_policy_errors(policy: Mapping[str, Any], branch: str, lock_present: bool) -> list[str]:
    branch_policy = (policy.get("branches") or {}).get(branch)
    if not isinstance(branch_policy, Mapping):
        return [f"branch policy for {branch} is missing"]
    errors = []
    if branch_policy.get("require_lock_file") and not lock_present:
        errors.append(f"{branch} requires awx.lock.yml")
    if branch == "production":
        if branch_policy.get("floating_upstream_refs_allowed"):
            errors.append("production must not allow floating upstream refs")
        if not branch_policy.get("require_publication_gate"):
            errors.append("production must require the publication gate")
        if not branch_policy.get("publication_allowed"):
            errors.append("production must allow intentional publication")
    return errors


def write_promotion_candidate(evidence_dir: Path, lock: Mapping[str, Any]) -> dict[str, Any]:
    data = {
        "schema_version": "awx-docker.promotion-candidate/v1",
        "status": "passed",
        "lock_file": "awx.lock.yml",
        "upstream": lock["upstream"],
        "image": {**lock["image"], "ref": image_ref(lock)},
        "promotion": lock["promotion"],
    }
    write_json(evidence_dir / "promotion-candidate.json", data)
    write_markdown(
        evidence_dir / "promotion-candidate.md",
        "Promotion Candidate",
        {
            "status": "`passed`",
            "image": f"`{data['image']['ref']}`",
            "repository": f"`{lock['upstream']['repository']}`",
            "requested_ref": f"`{lock['upstream']['requested_ref']}`",
            "resolved_revision": f"`{lock['upstream']['resolved_revision']}`",
            "lock_file": "`awx.lock.yml`",
        },
    )
    write_env(
        evidence_dir / "promotion-candidate.env",
        {
            "PROMOTION_CANDIDATE_STATUS": "passed",
            "IMAGE_REF": data["image"]["ref"],
            "UPSTREAM_REPOSITORY": lock["upstream"]["repository"],
            "UPSTREAM_REQUESTED_REF": lock["upstream"]["requested_ref"],
            "UPSTREAM_RESOLVED_REVISION": lock["upstream"]["resolved_revision"],
        },
    )
    return data


def write_production_admission(
    evidence_dir: Path,
    *,
    lock_present: bool,
    lock_errors: list[str],
    branch_errors: list[str],
    public_readiness_status: str,
    publication_gate_status: str,
    publication_gate_reason: str,
) -> dict[str, Any]:
    failures = [
        *lock_errors,
        *branch_errors,
        *(["public readiness failed"] if public_readiness_status == "fail" else []),
        *(["publication gate failed"] if publication_gate_status == "fail" else []),
    ]
    status = "fail" if failures else "pass"
    reason = "; ".join(failures) if failures else "Production admission passed."
    data = {
        "schema_version": "awx-docker.production-admission/v1",
        "status": status,
        "reason": reason,
        "checks": {
            "lock_file_present": lock_present,
            "lock_file": "pass" if lock_present and not lock_errors else "fail",
            "lock_file_reason": "; ".join(lock_errors) if lock_errors else "awx.lock.yml is valid.",
            "branch_policy": "pass" if not branch_errors else "fail",
            "branch_policy_reason": (
                "; ".join(branch_errors) if branch_errors else "production branch policy is valid."
            ),
            "public_readiness": public_readiness_status,
            "publication_gate": publication_gate_status,
            "publication_gate_reason": publication_gate_reason,
        },
    }
    write_json(evidence_dir / "production-admission.json", data)
    write_markdown(
        evidence_dir / "production-admission.md",
        "Production Admission",
        {
            "status": f"`{status}`",
            "reason": reason,
            "lock_file": f"`{data['checks']['lock_file']}`",
            "branch_policy": f"`{data['checks']['branch_policy']}`",
            "public_readiness": f"`{public_readiness_status}`",
            "publication_gate": f"`{publication_gate_status}`",
        },
    )
    return data


def write_production_pipeline(evidence_dir: Path, lock: Mapping[str, Any]) -> dict[str, Any]:
    data = {
        "schema_version": "awx-docker.production-pipeline/v1",
        "status": "passed",
        "lock_file": "awx.lock.yml",
        "upstream": lock["upstream"],
        "image": {**lock["image"], "ref": image_ref(lock)},
        "evidence": {
            "upstream_ref": "upstream-ref.json",
            "upstream_health": "upstream-health.json",
            "build_metadata": "build-metadata.json",
            "image_verification": "image-verification.json",
            "publication_gate": "publication-gate.json",
        },
    }
    write_json(evidence_dir / "production-pipeline.json", data)
    write_markdown(
        evidence_dir / "production-pipeline.md",
        "Production Pipeline",
        {
            "status": "`passed`",
            "image": f"`{data['image']['ref']}`",
            "repository": f"`{lock['upstream']['repository']}`",
            "requested_ref": f"`{lock['upstream']['requested_ref']}`",
            "resolved_revision": f"`{lock['upstream']['resolved_revision']}`",
            "lock_file": "`awx.lock.yml`",
        },
    )
    write_env(
        evidence_dir / "production-pipeline.env",
        {
            "PRODUCTION_PIPELINE_STATUS": "passed",
            "IMAGE_REF": data["image"]["ref"],
            "UPSTREAM_REPOSITORY": lock["upstream"]["repository"],
            "UPSTREAM_REQUESTED_REF": lock["upstream"]["requested_ref"],
            "UPSTREAM_RESOLVED_REVISION": lock["upstream"]["resolved_revision"],
        },
    )
    return data
