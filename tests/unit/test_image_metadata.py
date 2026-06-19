import json
from pathlib import Path

from awx_docker.image.metadata import write_build_metadata


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
