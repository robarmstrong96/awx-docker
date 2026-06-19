import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from awx_docker.cli import cmd_release_check


def test_release_check_prints_and_writes_blocking_reason(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(
        "awx_docker.cli.scan_public_hygiene",
        lambda root, policy_path, evidence: SimpleNamespace(status="pass"),
    )
    monkeypatch.setattr(
        "awx_docker.cli.write_upstream_health",
        lambda repo, ref, evidence, policy_path, mode, token: SimpleNamespace(
            decision=SimpleNamespace(
                state="fail",
                blocking=True,
                reason="SonarCloud Code Analysis (failure)",
            )
        ),
    )

    rc = cmd_release_check(
        argparse.Namespace(
            awx_repo="https://github.com/ansible/awx.git",
            awx_ref="devel",
            evidence_dir=str(tmp_path),
        )
    )

    assert rc == 1
    assert "release-check: fail (SonarCloud Code Analysis (failure))" in capsys.readouterr().out
    report = json.loads((tmp_path / "release-check.json").read_text())
    assert report["reason"] == "SonarCloud Code Analysis (failure)"
    assert report["checks"]["upstream_health_reason"] == "SonarCloud Code Analysis (failure)"
