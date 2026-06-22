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


def test_make_check_lint_format_and_test_are_dagger_aliases() -> None:
    assert dry_run("check") == "dagger call check --source=."
    assert dry_run("lint") == "dagger call lint --source=."
    assert dry_run("format") == "dagger call format --source=."
    assert dry_run("test") == "dagger call test --source=."


def test_make_image_targets_are_dagger_aliases() -> None:
    build = dry_run("build")
    verify = dry_run("verify")
    export = dry_run("export")

    assert "dagger call build --source=." in build
    assert "--upstream-ref=" in build
    assert "--image-name=" in build
    assert "--image-tag=" in build
    assert "dagger call verify --source=." in verify
    assert "export --path=build/evidence" in verify
    assert "dagger call export --source=." in export
    assert "--image-ref=" in export


def test_make_clean_removes_generated_artifacts() -> None:
    clean = dry_run("clean")

    assert "rm -rf build .pytest_cache .ruff_cache" in clean
    assert "-name __pycache__" in clean
    assert ".venv" in clean
    assert "rm -rf .venv" not in clean


def test_make_distclean_removes_virtualenv_after_clean() -> None:
    distclean = dry_run("distclean")

    assert "rm -rf build .pytest_cache .ruff_cache" in distclean
    assert "rm -rf .venv" in distclean


def test_makefile_does_not_expose_publication_or_production_targets() -> None:
    makefile = (ROOT / "Makefile").read_text()

    assert "public-readiness" not in makefile
    assert "publication-gate" not in makefile
    assert "production" not in makefile
    assert "image-publish" not in makefile
