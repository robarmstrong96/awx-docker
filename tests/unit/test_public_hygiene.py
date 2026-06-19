from pathlib import Path

import yaml

from awx_docker.public_hygiene.scan import scan_public_hygiene


def write_policy(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "schema": "awx-docker.public-hygiene/v1",
                "forbidden_patterns": [
                    {
                        "name": "local-home-path",
                        "pattern": "/" + "home/",
                        "severity": "fail",
                    },
                    {
                        "name": "dotenv-reference",
                        "pattern": r"\.env",
                        "severity": "warn",
                        "allowed_paths": [".gitignore"],
                    },
                ],
                "required_files": ["README.md"],
            },
            sort_keys=True,
        )
    )


def test_public_hygiene_forbidden_pattern_fails(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("ok\n")
    forbidden_path = "/" + "home/example"
    (tmp_path / "notes.txt").write_text(f"path {forbidden_path} should not ship\n")
    policy = tmp_path / "policy.yml"
    write_policy(policy)

    report = scan_public_hygiene(tmp_path, policy, tmp_path / "evidence")

    assert report.status == "fail"
    assert report.findings[0].name == "local-home-path"


def test_public_hygiene_allowed_path_exception(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("ok\n")
    (tmp_path / ".gitignore").write_text(".env\n")
    policy = tmp_path / "policy.yml"
    write_policy(policy)

    report = scan_public_hygiene(tmp_path, policy, tmp_path / "evidence")

    assert report.status == "pass"
    assert report.findings == []


def test_public_hygiene_missing_required_file_fails(tmp_path: Path) -> None:
    policy = tmp_path / "policy.yml"
    write_policy(policy)

    report = scan_public_hygiene(tmp_path, policy, tmp_path / "evidence")

    assert report.status == "fail"
    assert report.missing_required_files == ["README.md"]
