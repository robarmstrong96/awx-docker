import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from jsonschema import ValidationError, validate

from awx_docker.cli import cmd_publication_gate
from awx_docker.image.metadata import write_build_metadata
from awx_docker.image.pipeline import (
    write_image_pipeline,
    write_published_image,
    write_upstream_ref,
)
from awx_docker.production import (
    build_lock,
    write_production_admission,
    write_production_pipeline,
    write_promotion_candidate,
)
from awx_docker.public_readiness.scan import scan_public_readiness
from awx_docker.upstream.policy import load_policy
from awx_docker.upstream.report import build_report

ROOT = Path(__file__).resolve().parents[2]


def schema(name: str) -> dict:
    return json.loads((ROOT / f"schemas/{name}.schema.json").read_text())


def test_generated_reports_match_schemas(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    lock = build_lock(
        "https://github.com/ansible/awx.git",
        "devel",
        "1" * 40,
        "ghcr.io/example/awx-devel",
        "prod-2026-06-19-1111111",
        observed_at="2026-06-19T00:00:00Z",
    )
    validate(lock, schema("awx-lock"))

    metadata = write_build_metadata(
        tmp_path,
        evidence,
        "awx-devel",
        "devel",
        "https://github.com/ansible/awx.git",
        "devel",
        "a" * 40,
        "linux/amd64",
    )
    validate(metadata, schema("build-metadata"))

    readiness = scan_public_readiness(
        ROOT,
        ROOT / "policies/public-readiness.yml",
        evidence,
    )
    validate(readiness.to_dict(), schema("public-readiness"))

    combined = json.loads((ROOT / "tests/fixtures/github/healthy/combined-status.json").read_text())
    checks = json.loads((ROOT / "tests/fixtures/github/healthy/check-runs.json").read_text())
    upstream = build_report(
        "https://github.com/ansible/awx.git",
        "devel",
        "b" * 40,
        combined,
        checks,
        load_policy(ROOT / "policies/upstream-health.yml"),
        "scheduled-build",
    )
    validate(upstream.to_dict(), schema("upstream-health-report"))

    upstream_ref = write_upstream_ref(
        evidence,
        "https://github.com/ansible/awx.git",
        "devel",
        "d" * 40,
    )
    validate(upstream_ref, schema("upstream-ref"))

    image_pipeline = write_image_pipeline(
        evidence,
        "https://github.com/ansible/awx.git",
        "devel",
        "e" * 40,
        "awx-devel",
        "devel",
        "linux/amd64",
    )
    validate(image_pipeline, schema("image-pipeline"))

    published_image = write_published_image(
        evidence,
        "ghcr.io/example/awx-devel:devel",
        "ghcr.io/example/awx-devel:devel@sha256:" + "f" * 64,
        "https://github.com/ansible/awx.git",
        "devel",
        "f" * 40,
    )
    validate(published_image, schema("published-image"))

    promotion_candidate = write_promotion_candidate(evidence, lock)
    validate(promotion_candidate, schema("promotion-candidate"))

    production_admission = write_production_admission(
        evidence,
        lock_present=True,
        lock_errors=[],
        branch_errors=[],
        public_readiness_status="pass",
        publication_gate_status="pass",
        publication_gate_reason="Publication gate passed.",
    )
    validate(production_admission, schema("production-admission"))

    production_pipeline = write_production_pipeline(evidence, lock)
    validate(production_pipeline, schema("production-pipeline"))

    image_verification = {
        "schema_version": "awx-docker.image-verification/v1",
        "status": "passed",
        "image": {"ref": "awx-devel:devel"},
        "awx": {
            "git_metadata": "absent",
            "requested_ref": "devel",
            "source_revision": "c" * 40,
        },
    }
    validate(image_verification, schema("image-verification"))


def test_build_metadata_schema_requires_nested_contract(tmp_path: Path) -> None:
    metadata = write_build_metadata(
        tmp_path,
        tmp_path / "evidence",
        "awx-devel",
        "devel",
        "https://github.com/ansible/awx.git",
        "devel",
        "a" * 40,
        "linux/amd64",
    )
    del metadata["awx"]["resolved_ref"]

    with pytest.raises(ValidationError):
        validate(metadata, schema("build-metadata"))


def test_upstream_health_schema_requires_nested_contract() -> None:
    combined = json.loads((ROOT / "tests/fixtures/github/healthy/combined-status.json").read_text())
    checks = json.loads((ROOT / "tests/fixtures/github/healthy/check-runs.json").read_text())
    report = build_report(
        "https://github.com/ansible/awx.git",
        "devel",
        "b" * 40,
        combined,
        checks,
        load_policy(ROOT / "policies/upstream-health.yml"),
        "scheduled-build",
    ).to_dict()
    del report["signals"]["ci"]["blocking_failures"]

    with pytest.raises(ValidationError):
        validate(report, schema("upstream-health-report"))


def test_public_readiness_schema_requires_finding_contract(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("ok\n")
    forbidden_path = "/" + "home/example"
    (tmp_path / "notes.txt").write_text(f"path {forbidden_path} should not ship\n")
    policy = tmp_path / "policy.yml"
    policy.write_text(
        yaml.safe_dump(
            {
                "schema": "awx-docker.public-readiness/v1",
                "forbidden_patterns": [
                    {
                        "name": "local-home-path",
                        "pattern": "/" + "home/",
                        "severity": "fail",
                    }
                ],
                "required_files": ["README.md"],
            },
            sort_keys=True,
        )
    )
    report = scan_public_readiness(tmp_path, policy, tmp_path / "evidence").to_dict()
    del report["findings"][0]["line"]

    with pytest.raises(ValidationError):
        validate(report, schema("public-readiness"))


def test_generated_publication_gate_matches_schema(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "awx_docker.cli.scan_public_readiness",
        lambda root, policy_path, evidence: SimpleNamespace(status="pass"),
    )
    monkeypatch.setattr(
        "awx_docker.cli.write_upstream_health",
        lambda *args, **kwargs: SimpleNamespace(
            decision=SimpleNamespace(
                state="pass",
                blocking=False,
                reason="No blocking upstream provider signals were found.",
            )
        ),
    )

    rc = cmd_publication_gate(
        argparse.Namespace(
            upstream_repository="https://github.com/ansible/awx.git",
            upstream_ref="devel",
            provider="auto",
            signal_file=None,
            resolved_revision=None,
            from_lock=False,
            purpose="repository",
            evidence_dir=str(tmp_path),
        )
    )

    assert rc == 0
    publication_gate = json.loads((tmp_path / "publication-gate.json").read_text())
    validate(publication_gate, schema("publication-gate"))


def test_checked_in_lockfile_matches_schema() -> None:
    lock = yaml.safe_load((ROOT / "awx.lock.yml").read_text())

    validate(lock, schema("awx-lock"))
