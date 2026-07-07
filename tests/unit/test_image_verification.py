import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_image_verification_evidence_writer(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"

    subprocess.run(
        [
            "python3",
            "docker/awx/bin/write-image-verification-evidence",
            "--evidence-dir",
            str(evidence_dir),
            "--image-ref",
            "awx-devel:devel",
            "--requested-ref",
            "devel",
            "--source-revision",
            "a" * 40,
        ],
        cwd=ROOT,
        check=True,
    )

    data = json.loads((evidence_dir / "image-verification.json").read_text())

    assert data == {
        "awx": {
            "git_metadata": "absent",
            "requested_ref": "devel",
            "source_revision": "a" * 40,
        },
        "image": {
            "ref": "awx-devel:devel",
        },
        "schema_version": "awx-docker.image-verification/v1",
        "status": "passed",
    }
    assert "AWX Image Verification" in (evidence_dir / "image-verification.md").read_text()
