import json
from pathlib import Path
from urllib.parse import urlparse

import requests


def github_repo_path(repo_url: str) -> str:
    parsed = urlparse(repo_url)
    if parsed.netloc != "github.com":
        raise ValueError(f"unsupported upstream repository URL: {repo_url}")
    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if path.count("/") != 1:
        raise ValueError(f"unsupported upstream repository URL: {repo_url}")
    return path


def fetch_signals(repo_url: str, sha: str, token: str | None = None) -> tuple[dict, dict]:
    repo_path = github_repo_path(repo_url)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    combined_url = f"https://api.github.com/repos/{repo_path}/commits/{sha}/status"
    checks_url = f"https://api.github.com/repos/{repo_path}/commits/{sha}/check-runs?per_page=100"
    combined = requests.get(combined_url, headers=headers, timeout=30)
    combined.raise_for_status()
    checks = requests.get(checks_url, headers=headers, timeout=30)
    checks.raise_for_status()
    return combined.json(), checks.json()


def write_raw(raw_dir: Path, combined: dict, checks: dict) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "combined-status.json").write_text(
        json.dumps(combined, indent=2, sort_keys=True) + "\n"
    )
    (raw_dir / "check-runs.json").write_text(json.dumps(checks, indent=2, sort_keys=True) + "\n")
