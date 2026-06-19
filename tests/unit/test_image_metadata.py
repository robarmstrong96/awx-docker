import json
from pathlib import Path

from awx_docker.image.metadata import write_build_metadata
from awx_docker.image.pipeline import write_image_pipeline, write_upstream_ref


def test_build_metadata_writes_stable_json(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"

    data = write_build_metadata(
        tmp_path,
        evidence,
        "awx-devel",
        "devel",
        "https://github.com/ansible/awx.git",
        "devel",
        "a" * 40,
        "linux/amd64",
    )

    written = json.loads((evidence / "build-metadata.json").read_text())
    assert written == data
    assert list(written) == ["awx", "image", "platform", "schema_version", "wrapper_revision"]
    assert (evidence / "build-metadata.md").exists()


def test_upstream_ref_writes_resolved_revision_evidence(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"

    data = write_upstream_ref(
        evidence,
        "https://github.com/ansible/awx.git",
        "devel",
        "b" * 40,
    )

    written = json.loads((evidence / "upstream-ref.json").read_text())
    assert written == data
    assert written["resolved_revision"] == "b" * 40
    assert (evidence / "upstream-ref.md").exists()
    assert "UPSTREAM_RESOLVED_REVISION=" + "b" * 40 in (evidence / "upstream-ref.env").read_text()


def test_image_pipeline_writes_summary_evidence(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"

    data = write_image_pipeline(
        evidence,
        "https://github.com/ansible/awx.git",
        "devel",
        "c" * 40,
        "awx-devel",
        "devel",
        "linux/amd64",
    )

    written = json.loads((evidence / "image-pipeline.json").read_text())
    assert written == data
    assert written["status"] == "passed"
    assert written["upstream"]["resolved_revision"] == "c" * 40
    assert written["evidence"]["image_verification"] == "image-verification.json"
