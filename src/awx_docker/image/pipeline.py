from pathlib import Path

from awx_docker.evidence import write_env, write_json, write_markdown


def write_upstream_ref(
    evidence_dir: Path,
    repository: str,
    requested_ref: str,
    resolved_revision: str,
) -> dict:
    data = {
        "schema_version": "awx-docker.upstream-ref/v1",
        "repository": repository,
        "requested_ref": requested_ref,
        "resolved_revision": resolved_revision,
    }
    write_json(evidence_dir / "upstream-ref.json", data)
    write_markdown(
        evidence_dir / "upstream-ref.md",
        "Resolved Upstream Ref",
        {
            "repository": f"`{repository}`",
            "requested_ref": f"`{requested_ref}`",
            "resolved_revision": f"`{resolved_revision}`",
        },
    )
    write_env(
        evidence_dir / "upstream-ref.env",
        {
            "UPSTREAM_REPOSITORY": repository,
            "UPSTREAM_REQUESTED_REF": requested_ref,
            "UPSTREAM_RESOLVED_REVISION": resolved_revision,
        },
    )
    return data
