import json
from pathlib import Path

from jsonschema import validate

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
