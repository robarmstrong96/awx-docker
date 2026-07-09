"""Small Git helpers used to pin upstream AWX source refs."""

import re
import subprocess
import tempfile
from pathlib import Path

FULL_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def resolve_ref(repo: str, ref: str) -> str:
    """Resolve a branch, tag, or SHA to the commit SHA Docker should build.

    Parameters
    ----------
    repo : str
        Git repository to query.
    ref : str
        Branch, tag, or commit SHA to resolve.

    Returns
    -------
    str
        Concrete commit SHA.

    Raises
    ------
    RuntimeError
        Raised when the requested ref cannot be found in the repository.
    subprocess.CalledProcessError
        Raised when ``git ls-remote`` fails.
    """
    if FULL_SHA_RE.match(ref):
        return ref

    result = subprocess.run(
        [
            "git",
            "ls-remote",
            repo,
            ref,
            f"refs/heads/{ref}",
            f"refs/tags/{ref}",
            f"refs/tags/{ref}^{{}}",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    refs = [line.split() for line in result.stdout.splitlines() if line.split()]
    if not refs:
        raise RuntimeError(f"unable to resolve AWX ref {ref!r} from {repo}")

    first = refs[0][0]
    head = ""
    tag = ""
    peeled = ""
    for sha, name in refs:
        if name.endswith("^{}"):
            peeled = sha
        elif name.startswith("refs/heads/"):
            head = sha
        elif name.startswith("refs/tags/"):
            tag = sha

    return peeled or head or tag or first


def verify_revision_reachable(repo: str, revision: str) -> bool:
    """Return whether a commit SHA can be fetched from the given repository.

    Parameters
    ----------
    repo : str
        Git repository to fetch from.
    revision : str
        Commit SHA to verify.

    Returns
    -------
    bool
        True when the revision can be fetched and resolves to a commit.
    """
    if not FULL_SHA_RE.match(revision):
        return False

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)
        subprocess.run(["git", "init"], cwd=path, check=True, text=True, capture_output=True)
        fetched = subprocess.run(
            ["git", "fetch", "--depth=1", repo, revision],
            cwd=path,
            check=False,
            text=True,
            capture_output=True,
        )
        if fetched.returncode != 0:
            return False
        checked = subprocess.run(
            ["git", "cat-file", "-e", f"{revision}^{{commit}}"],
            cwd=path,
            check=False,
            text=True,
            capture_output=True,
        )
        return checked.returncode == 0
