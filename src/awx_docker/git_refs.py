import re
import subprocess

FULL_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def resolve_ref(repo: str, ref: str) -> str:
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
