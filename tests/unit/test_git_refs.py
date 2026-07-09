import subprocess
from pathlib import Path

import pytest

from awx_docker.git_refs import resolve_ref


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


@pytest.fixture
def repo_with_refs(tmp_path: Path) -> tuple[str, dict[str, str]]:
    repo = tmp_path / "repo"
    repo.mkdir()

    git(repo, "init")
    git(repo, "config", "user.email", "awx-docker@example.invalid")
    git(repo, "config", "user.name", "AWX Docker Tests")

    git(repo, "commit", "--allow-empty", "-m", "branch target")
    branch_sha = git(repo, "rev-parse", "HEAD")
    git(repo, "branch", "devel")

    git(repo, "commit", "--allow-empty", "-m", "lightweight tag target")
    lightweight_tag_sha = git(repo, "rev-parse", "HEAD")
    git(repo, "tag", "lightweight")

    git(repo, "commit", "--allow-empty", "-m", "annotated tag target")
    annotated_tag_sha = git(repo, "rev-parse", "HEAD")
    git(repo, "tag", "-a", "annotated", "-m", "annotated tag")

    return (
        str(repo),
        {
            "devel": branch_sha,
            "lightweight": lightweight_tag_sha,
            "annotated": annotated_tag_sha,
        },
    )


def test_resolve_ref_returns_full_sha_without_network() -> None:
    commit_sha = "a" * 40
    assert resolve_ref("https://github.com/ansible/awx.git", commit_sha) == commit_sha


@pytest.mark.parametrize(
    "ref_type",
    [
        pytest.param("devel", id="branch"),
        pytest.param("lightweight", id="lightweight-tag"),
        pytest.param("annotated", id="annotated-tag"),
    ],
)
def test_resolve_ref_prefers_branch_tag_and_peeled_tag(
    repo_with_refs: tuple[str, dict[str, str]],
    ref_type: str,
) -> None:
    repo, expected = repo_with_refs

    assert resolve_ref(repo, ref_type) == expected[ref_type]
