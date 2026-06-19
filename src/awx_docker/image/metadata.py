import subprocess
from pathlib import Path

from awx_docker.evidence import write_env, write_json, write_markdown


def wrapper_revision(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def write_build_metadata(
    root: Path,
    evidence_dir: Path,
    image_name: str,
    image_tag: str,
    awx_repo: str,
    requested_ref: str,
    resolved_ref: str,
    platform: str,
) -> dict:
    data = {
        "schema_version": "awx-docker.build-metadata/v1",
        "image": {"name": image_name, "tag": image_tag, "ref": f"{image_name}:{image_tag}"},
        "awx": {"repo": awx_repo, "requested_ref": requested_ref, "resolved_ref": resolved_ref},
        "wrapper_revision": wrapper_revision(root),
        "platform": platform,
    }
    write_json(evidence_dir / "build-metadata.json", data)
    write_markdown(
        evidence_dir / "build-metadata.md",
        "AWX Image Build Metadata",
        {
            "image": f"`{image_name}:{image_tag}`",
            "awx_repo": f"`{awx_repo}`",
            "awx_requested_ref": f"`{requested_ref}`",
            "awx_resolved_ref": f"`{resolved_ref}`",
            "wrapper_revision": f"`{data['wrapper_revision']}`",
            "platform": f"`{platform}`",
        },
    )
    write_env(
        evidence_dir / "build-metadata.env",
        {
            "IMAGE_REF": f"{image_name}:{image_tag}",
            "IMAGE_NAME": image_name,
            "IMAGE_TAG": image_tag,
            "AWX_REPO": awx_repo,
            "AWX_REQUESTED_REF": requested_ref,
            "AWX_RESOLVED_REF": resolved_ref,
            "WRAPPER_REVISION": data["wrapper_revision"],
            "PLATFORM": platform,
        },
    )
    return data
