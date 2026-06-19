from urllib.parse import urlparse

from awx_docker.upstream.providers import file, generic_git, github

PROVIDERS = {
    "file": file.collect,
    "generic-git": generic_git.collect,
    "github": github.collect,
}


def select_provider(repository: str, requested_provider: str):
    provider = requested_provider.lower()
    if provider == "auto":
        provider = "github" if urlparse(repository).netloc == "github.com" else "generic-git"
    if provider == "github" and urlparse(repository).netloc != "github.com":
        raise ValueError("--provider=github requires a github.com repository URL")
    if provider not in PROVIDERS:
        supported = ", ".join(["auto", *sorted(PROVIDERS)])
        raise ValueError(
            f"unsupported upstream provider {requested_provider!r}; use one of {supported}"
        )
    return provider, PROVIDERS[provider]
