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


def test_just_build_recipe_runs_dagger_build_with_ui_pin() -> None:
    build = recipe_body("build")

    assert "dagger call build --source=." in build
    assert "--upstream-ref=" in build
    assert "--awx-ui-ref=" in build
    assert "--image-name=" in build
    assert "--image-tag=" in build
