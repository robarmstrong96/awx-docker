import re
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from awx_docker.evidence import write_json, write_markdown


@dataclass(frozen=True)
class Finding:
    name: str
    severity: str
    path: str
    line: int
    text: str


@dataclass(frozen=True)
class PublicReadinessReport:
    schema_version: str
    status: str
    findings: list[Finding]
    missing_required_files: list[str]

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "findings": [asdict(finding) for finding in self.findings],
            "missing_required_files": self.missing_required_files,
        }


def _iter_files(root: Path) -> list[Path]:
    ignored_dirs = {".git", ".venv", "build", "__pycache__", ".pytest_cache", ".ruff_cache"}
    files = []
    for path in root.rglob("*"):
        if any(part in ignored_dirs for part in path.parts):
            continue
        if path.is_file():
            files.append(path)
    return files


def scan_public_readiness(
    root: Path, policy_path: Path, evidence_dir: Path
) -> PublicReadinessReport:
    policy = yaml.safe_load(policy_path.read_text())
    policy_path = policy_path.resolve()
    findings: list[Finding] = []

    for file_path in _iter_files(root):
        if file_path.resolve() == policy_path:
            continue
        rel = file_path.relative_to(root).as_posix()
        try:
            lines = file_path.read_text(errors="ignore").splitlines()
        except UnicodeDecodeError:
            continue
        for rule in policy.get("forbidden_patterns", []):
            allowed = set(rule.get("allowed_paths", []))
            if rel in allowed:
                continue
            pattern = re.compile(rule["pattern"])
            for index, line in enumerate(lines, start=1):
                if pattern.search(line):
                    findings.append(
                        Finding(
                            name=rule["name"],
                            severity=rule["severity"],
                            path=rel,
                            line=index,
                            text=line.strip(),
                        )
                    )

    missing = [path for path in policy.get("required_files", []) if not (root / path).exists()]
    status = "fail" if missing or any(f.severity == "fail" for f in findings) else "pass"
    report = PublicReadinessReport(
        schema_version=policy["schema"],
        status=status,
        findings=findings,
        missing_required_files=missing,
    )

    write_json(evidence_dir / "public-readiness.json", report.to_dict())
    write_markdown(
        evidence_dir / "public-readiness.md",
        "Public Readiness",
        {
            "status": f"`{status}`",
            "findings": str(len(findings)),
            "missing_required_files": str(len(missing)),
        },
    )
    return report
