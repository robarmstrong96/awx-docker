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


def write_image_pipeline(
    evidence_dir: Path,
    repository: str,
    requested_ref: str,
    resolved_revision: str,
    image_name: str,
    image_tag: str,
    platform: str,
) -> dict:
    image_ref = f"{image_name}:{image_tag}"
    data = {
        "schema_version": "awx-docker.image-pipeline/v1",
        "status": "passed",
        "upstream": {
            "repository": repository,
            "requested_ref": requested_ref,
            "resolved_revision": resolved_revision,
        },
        "image": {"name": image_name, "tag": image_tag, "ref": image_ref},
        "platform": platform,
        "evidence": {
            "upstream_ref": "upstream-ref.json",
            "upstream_health": "upstream-health.json",
            "build_metadata": "build-metadata.json",
            "image_verification": "image-verification.json",
        },
    }
    write_json(evidence_dir / "image-pipeline.json", data)
    write_markdown(
        evidence_dir / "image-pipeline.md",
        "Image Pipeline",
        {
            "status": "`passed`",
            "image": f"`{image_ref}`",
            "repository": f"`{repository}`",
            "requested_ref": f"`{requested_ref}`",
            "resolved_revision": f"`{resolved_revision}`",
            "platform": f"`{platform}`",
        },
    )
    write_env(
        evidence_dir / "image-pipeline.env",
        {
            "IMAGE_PIPELINE_STATUS": "passed",
            "IMAGE_REF": image_ref,
            "UPSTREAM_REPOSITORY": repository,
            "UPSTREAM_REQUESTED_REF": requested_ref,
            "UPSTREAM_RESOLVED_REVISION": resolved_revision,
            "PLATFORM": platform,
        },
    )
    return data


def write_published_image(
    evidence_dir: Path,
    image_ref: str,
    published_ref: str,
    repository: str,
    requested_ref: str,
    resolved_revision: str,
) -> dict:
    data = {
        "schema_version": "awx-docker.published-image/v1",
        "image": {"requested_ref": image_ref, "published_ref": published_ref},
        "upstream": {
            "repository": repository,
            "requested_ref": requested_ref,
            "resolved_revision": resolved_revision,
        },
    }
    write_json(evidence_dir / "published-image.json", data)
    write_markdown(
        evidence_dir / "published-image.md",
        "Published Image",
        {
            "requested_ref": f"`{image_ref}`",
            "published_ref": f"`{published_ref}`",
            "repository": f"`{repository}`",
            "upstream_ref": f"`{requested_ref}`",
            "resolved_revision": f"`{resolved_revision}`",
        },
    )
    write_env(
        evidence_dir / "published-image.env",
        {
            "IMAGE_REF": image_ref,
            "PUBLISHED_IMAGE_REF": published_ref,
            "UPSTREAM_REPOSITORY": repository,
            "UPSTREAM_REQUESTED_REF": requested_ref,
            "UPSTREAM_RESOLVED_REVISION": resolved_revision,
        },
    )
    return data
