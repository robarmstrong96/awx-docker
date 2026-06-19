from typing import Any

from awx_docker.upstream.github_client import fetch_signals, github_repo_path


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


def test_fetch_signals_uses_policy_check_run_page_size(monkeypatch) -> None:
    urls = []

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        urls.append(url)
        if url.endswith("/status"):
            return FakeResponse({"state": "success", "statuses": []})
        return FakeResponse({"check_runs": [], "total_count": 0})

    monkeypatch.setattr("awx_docker.upstream.github_client.requests.get", fake_get)

    fetch_signals("https://github.com/ansible/awx.git", "a" * 40, checks_per_page=42)

    assert urls == [
        f"https://api.github.com/repos/ansible/awx/commits/{'a' * 40}/status",
        f"https://api.github.com/repos/ansible/awx/commits/{'a' * 40}/check-runs?per_page=42",
    ]


def test_github_repo_path_accepts_https_git_url() -> None:
    assert github_repo_path("https://github.com/ansible/awx.git") == "ansible/awx"
