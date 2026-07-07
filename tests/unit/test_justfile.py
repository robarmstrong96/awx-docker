import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def recipe_body(recipe: str) -> str:
    justfile = (ROOT / "justfile").read_text()
    match = re.search(rf"^{recipe}:[^\n]*\n(?P<body>(?:    .*\n?)*)", justfile, re.MULTILINE)

    assert match is not None
    return match.group("body").strip()


def test_justfile_parses_when_just_is_available() -> None:
    if not shutil.which("just"):
        return

    subprocess.run(["just", "--summary"], cwd=ROOT, check=True, capture_output=True, text=True)


def test_just_lint_recipe_runs_dagger_lint() -> None:
    assert recipe_body("lint") == "dagger call lint --source=."


def test_just_build_recipe_delegates_to_dagger_defaults() -> None:
    assert recipe_body("build") == "dagger call build --source=."


def test_just_verify_recipe_exports_default_evidence_path() -> None:
    assert recipe_body("verify") == "dagger call verify --source=. export --path=build/evidence"


def test_just_export_recipe_exports_default_tarball_path() -> None:
    assert recipe_body("export") == (
        "dagger call export --source=. export --path=build/out/awx-devel.tar"
    )
