"""Tests for resolving upstream AWX Git refs."""

import subprocess
from pathlib import Path

from awx_docker.git_refs import resolve_ref


def git(repo: Path, *args: str) -> str:
    """Run a Git command in a test repository and return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def test_resolve_ref_returns_full_sha_without_network() -> None:
    """A full SHA should pass through without running git ls-remote."""
    commit_sha = "a" * 40
    assert resolve_ref("https://github.com/ansible/awx.git", commit_sha) == commit_sha


def test_resolve_ref_prefers_peeled_annotated_tag(tmp_path: Path) -> None:
    """Annotated tags should resolve to the commit, not the tag object."""
    repo = tmp_path / "repo"
    repo.mkdir()

    git(repo, "init")
    git(repo, "config", "user.email", "awx-docker@example.invalid")
    git(repo, "config", "user.name", "AWX Docker Tests")

    git(repo, "commit", "--allow-empty", "-m", "branch target")
    expected = git(repo, "rev-parse", "HEAD")
    git(repo, "tag", "-a", "annotated", "-m", "annotated tag")

    assert resolve_ref(str(repo), "annotated") == expected
