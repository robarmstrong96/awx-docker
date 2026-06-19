import subprocess

import pytest

from awx_docker.git_refs import resolve_ref


def test_resolve_ref_returns_full_sha_without_network() -> None:
    sha = "a" * 40
    assert resolve_ref("https://github.com/ansible/awx.git", sha) == sha


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        ("1" * 40 + "\trefs/heads/devel\n", "1" * 40),
        ("2" * 40 + "\trefs/tags/1.0.0\n", "2" * 40),
        (
            "3" * 40 + "\trefs/tags/1.0.0\n" + "4" * 40 + "\trefs/tags/1.0.0^{}\n",
            "4" * 40,
        ),
    ],
)
def test_resolve_ref_prefers_branch_tag_and_peeled_tag(
    monkeypatch: pytest.MonkeyPatch,
    stdout: str,
    expected: str,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=["git"], returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert resolve_ref("https://github.com/ansible/awx.git", "devel") == expected
