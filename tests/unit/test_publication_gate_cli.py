import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from awx_docker.cli import cmd_publication_gate


def test_publication_gate_prints_and_writes_blocking_reason(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(
        "awx_docker.cli.scan_public_readiness",
        lambda root, policy_path, evidence: SimpleNamespace(status="pass"),
    )
    monkeypatch.setattr(
        "awx_docker.cli.write_upstream_health",
        lambda *args, **kwargs: SimpleNamespace(
            decision=SimpleNamespace(
                state="fail",
                blocking=True,
                reason="SonarCloud Code Analysis (failure)",
            )
        ),
    )

    rc = cmd_publication_gate(
        argparse.Namespace(
            upstream_repository="https://github.com/ansible/awx.git",
            upstream_ref="devel",
            provider="auto",
            signal_file=None,
            resolved_revision=None,
            from_lock=False,
            purpose="repository",
            evidence_dir=str(tmp_path),
        )
    )

    assert rc == 1
    assert "publication-gate: fail (SonarCloud Code Analysis (failure))" in capsys.readouterr().out
    report = json.loads((tmp_path / "publication-gate.json").read_text())
    assert report["reason"] == "SonarCloud Code Analysis (failure)"
    assert report["checks"]["upstream_health_reason"] == "SonarCloud Code Analysis (failure)"


def test_publication_gate_requires_image_verification_for_image_publication(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "awx_docker.cli.scan_public_readiness",
        lambda root, policy_path, evidence: SimpleNamespace(status="pass"),
    )
    monkeypatch.setattr(
        "awx_docker.cli.write_upstream_health",
        lambda *args, **kwargs: SimpleNamespace(
            decision=SimpleNamespace(
                state="pass",
                blocking=False,
                reason="No blocking upstream provider signals were found.",
            )
        ),
    )

    rc = cmd_publication_gate(
        argparse.Namespace(
            upstream_repository="https://github.com/ansible/awx.git",
            upstream_ref="devel",
            provider="auto",
            signal_file=None,
            resolved_revision=None,
            from_lock=False,
            purpose="image-publication",
            evidence_dir=str(tmp_path),
        )
    )

    assert rc == 1
    report = json.loads((tmp_path / "publication-gate.json").read_text())
    assert report["purpose"] == "image-publication"
    assert report["checks"]["image_verification"] == "fail"
