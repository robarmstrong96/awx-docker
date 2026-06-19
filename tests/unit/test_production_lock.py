import argparse
import json
from pathlib import Path

import yaml

from awx_docker import cli
from awx_docker.production import (
    build_lock,
    load_lock,
    validate_lock,
    write_lock,
    write_production_admission,
    write_production_pipeline,
    write_promotion_candidate,
)
from awx_docker.production.lock import branch_policy_errors


def test_lockfile_validation_accepts_pinned_revision() -> None:
    lock = build_lock(
        "https://github.com/ansible/awx.git",
        "devel",
        "a" * 40,
        "ghcr.io/example/awx-devel",
        "prod-2026-06-19-aaaaaaa",
        observed_at="2026-06-19T00:00:00Z",
    )

    assert validate_lock(lock) == []


def test_lockfile_validation_requires_promotion_evidence_for_production() -> None:
    lock = build_lock(
        "https://github.com/ansible/awx.git",
        "devel",
        "a" * 40,
        "ghcr.io/example/awx-devel",
        "prod-2026-06-19-aaaaaaa",
        observed_at="2026-06-19T00:00:00Z",
    )

    assert validate_lock(lock, require_promotion_evidence=True) == [
        "promotion.promoted_by is required for production admission",
        "promotion.evidence_run_url or promotion.evidence_waiver is required "
        "for production admission",
    ]


def test_lockfile_validation_accepts_promotion_evidence_waiver() -> None:
    lock = build_lock(
        "https://github.com/ansible/awx.git",
        "devel",
        "a" * 40,
        "ghcr.io/example/awx-devel",
        "prod-2026-06-19-aaaaaaa",
        observed_at="2026-06-19T00:00:00Z",
        promoted_by="repository-maintainer",
        evidence_waiver="manual admission test",
    )

    assert validate_lock(lock, require_promotion_evidence=True) == []


def test_lockfile_validation_rejects_floating_revision() -> None:
    lock = build_lock(
        "https://github.com/ansible/awx.git",
        "devel",
        "devel",
        "ghcr.io/example/awx-devel",
        "prod-2026-06-19-aaaaaaa",
    )

    assert validate_lock(lock) == ["upstream.resolved_revision must be a 40-character git SHA"]


def test_production_branch_policy_rejects_floating_refs() -> None:
    policy = {
        "branches": {
            "production": {
                "floating_upstream_refs_allowed": True,
                "require_lock_file": True,
                "publication_allowed": True,
                "require_publication_gate": True,
            }
        }
    }

    assert branch_policy_errors(policy, "production", lock_present=True) == [
        "production must not allow floating upstream refs"
    ]


def test_promote_candidate_writes_valid_lock_and_evidence(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "root_dir", lambda: tmp_path)

    rc = cli.cmd_promote_candidate(
        argparse.Namespace(
            upstream_repository="https://github.com/ansible/awx.git",
            upstream_ref="devel",
            resolved_revision="b" * 40,
            image_name="ghcr.io/example/awx-devel",
            image_tag="prod-2026-06-19-bbbbbbb",
            promoted_by="",
            evidence_run_url="",
            evidence_waiver="",
            notes="",
            evidence_dir=str(tmp_path / "evidence"),
        )
    )

    assert rc == 0
    lock = load_lock(tmp_path / "awx.lock.yml")
    assert validate_lock(lock) == []
    assert lock["upstream"]["resolved_revision"] == "b" * 40
    candidate = json.loads((tmp_path / "evidence/promotion-candidate.json").read_text())
    assert candidate["lock_file"] == "awx.lock.yml"


def test_production_admission_fails_when_lockfile_is_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "root_dir", lambda: tmp_path)
    (tmp_path / "README.md").write_text("ok\n")
    (tmp_path / "policies").mkdir()
    (tmp_path / "policies/public-readiness.yml").write_text(
        yaml.safe_dump(
            {
                "schema": "awx-docker.public-readiness/v1",
                "forbidden_patterns": [],
                "required_files": ["README.md"],
            }
        )
    )
    (tmp_path / "policies/branches.yml").write_text(
        yaml.safe_dump(
            {
                "schema": "awx-docker.branch-policy/v1",
                "branches": {
                    "production": {
                        "floating_upstream_refs_allowed": False,
                        "scheduled_upstream_discovery": False,
                        "require_lock_file": True,
                        "publication_allowed": True,
                        "require_publication_gate": True,
                    }
                },
            }
        )
    )

    rc = cli.cmd_production_admission(
        argparse.Namespace(provider="generic-git", signal_file=None, evidence_dir=str(tmp_path))
    )

    assert rc == 1
    report = json.loads((tmp_path / "production-admission.json").read_text())
    assert report["status"] == "fail"
    assert report["checks"]["lock_file_present"] is False


def test_production_pipeline_evidence_uses_locked_revision(tmp_path: Path) -> None:
    lock = build_lock(
        "https://github.com/ansible/awx.git",
        "devel",
        "c" * 40,
        "ghcr.io/example/awx-devel",
        "prod-2026-06-19-ccccccc",
    )
    write_lock(tmp_path / "awx.lock.yml", lock)
    written = load_lock(tmp_path / "awx.lock.yml")

    data = write_production_pipeline(tmp_path / "evidence", written)

    assert data["upstream"]["requested_ref"] == "devel"
    assert data["upstream"]["resolved_revision"] == "c" * 40
    assert data["image"]["ref"] == "ghcr.io/example/awx-devel:prod-2026-06-19-ccccccc"


def test_production_admission_evidence_passes_with_valid_inputs(tmp_path: Path) -> None:
    data = write_production_admission(
        tmp_path,
        lock_present=True,
        lock_errors=[],
        branch_errors=[],
        public_readiness_status="pass",
        publication_gate_status="pass",
        publication_gate_reason="Publication gate passed.",
    )

    assert data["status"] == "pass"
    assert data["checks"]["lock_file"] == "pass"


def test_promotion_candidate_evidence_uses_lockfile(tmp_path: Path) -> None:
    lock = build_lock(
        "https://github.com/ansible/awx.git",
        "devel",
        "d" * 40,
        "ghcr.io/example/awx-devel",
        "prod-2026-06-19-ddddddd",
    )

    data = write_promotion_candidate(tmp_path, lock)

    assert data["status"] == "passed"
    assert data["upstream"]["resolved_revision"] == "d" * 40
