import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def dry_run(target: str) -> str:
    result = subprocess.run(
        ["make", "-n", target],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_make_check_is_dagger_shim() -> None:
    assert dry_run("check") == "dagger call check --source=."


def test_make_upstream_health_is_dagger_shim() -> None:
    assert (
        dry_run("upstream-health")
        == 'dagger call upstream-health --source=. --awx-ref="${AWX_REF:-devel}"'
    )


def test_make_image_targets_are_dagger_shims() -> None:
    assert dry_run("build") == (
        'dagger call image-build --source=. --awx-ref="${AWX_REF:-devel}" '
        '--image-name="${IMAGE_NAME:-awx-devel}" --image-tag="${IMAGE_TAG:-devel}"'
    )
    assert dry_run("verify-image") == (
        'dagger call image-verify --source=. --awx-ref="${AWX_REF:-devel}" '
        '--image-name="${IMAGE_NAME:-awx-devel}" --image-tag="${IMAGE_TAG:-devel}"'
    )


def test_make_release_and_evidence_targets_are_dagger_shims() -> None:
    assert (
        dry_run("release-check")
        == 'dagger call release-check --source=. --awx-ref="${AWX_REF:-devel}"'
    )
    assert dry_run("evidence") == "dagger call evidence --source=."
