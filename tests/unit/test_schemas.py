import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from jsonschema import validate

from awx_docker.cli import cmd_release_check
from awx_docker.image.metadata import write_build_metadata
from awx_docker.public_hygiene.scan import scan_public_hygiene
from awx_docker.upstream.policy import load_policy
from awx_docker.upstream.report import build_report

ROOT = Path(__file__).resolve().parents[2]


def schema(name: str) -> dict:
    return json.loads((ROOT / f"schemas/{name}.schema.json").read_text())


def test_generated_reports_match_schemas(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
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

    hygiene = scan_public_hygiene(
        ROOT,
        ROOT / "policies/public-hygiene.yml",
        evidence,
    )
    validate(hygiene.to_dict(), schema("public-hygiene"))

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


def test_generated_release_check_matches_schema(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "awx_docker.cli.scan_public_hygiene",
        lambda root, policy_path, evidence: SimpleNamespace(status="pass"),
    )
    monkeypatch.setattr(
        "awx_docker.cli.write_upstream_health",
        lambda repo, ref, evidence, policy_path, mode, token: SimpleNamespace(
            decision=SimpleNamespace(
                state="pass",
                blocking=False,
                reason="No failing or incomplete upstream statuses/check runs were found.",
            )
        ),
    )

    rc = cmd_release_check(
        argparse.Namespace(
            awx_repo="https://github.com/ansible/awx.git",
            awx_ref="devel",
            evidence_dir=str(tmp_path),
        )
    )

    assert rc == 0
    release_check = json.loads((tmp_path / "release-check.json").read_text())
    validate(release_check, schema("release-check"))
