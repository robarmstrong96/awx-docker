import argparse
import os
from pathlib import Path

from awx_docker.config import (
    DEFAULT_AWX_REF,
    DEFAULT_AWX_REPO,
    DEFAULT_EVIDENCE_DIR,
    DEFAULT_IMAGE_NAME,
    DEFAULT_IMAGE_TAG,
    DEFAULT_PLATFORM,
)
from awx_docker.evidence import write_json, write_markdown
from awx_docker.git_refs import resolve_ref
from awx_docker.image.metadata import write_build_metadata
from awx_docker.image.pipeline import (
    write_image_pipeline,
    write_published_image,
    write_upstream_ref,
)
from awx_docker.public_hygiene import scan_public_hygiene
from awx_docker.upstream import write_upstream_health


def root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def evidence_dir(value: str | None = None) -> Path:
    return Path(value or os.environ.get("EVIDENCE_DIR", DEFAULT_EVIDENCE_DIR))


def cmd_resolve_ref(args: argparse.Namespace) -> int:
    print(resolve_ref(args.awx_repo, args.awx_ref))
    return 0


def cmd_write_metadata(args: argparse.Namespace) -> int:
    resolved = args.awx_resolved_ref or resolve_ref(args.awx_repo, args.awx_ref)
    write_build_metadata(
        root_dir(),
        evidence_dir(args.evidence_dir),
        args.image_name,
        args.image_tag,
        args.awx_repo,
        args.awx_requested_ref or args.awx_ref,
        resolved,
        args.platform,
    )
    print(f"build-metadata: ok ({resolved})")
    return 0


def cmd_write_upstream_ref(args: argparse.Namespace) -> int:
    resolved = args.resolved_revision or resolve_ref(args.upstream_repository, args.upstream_ref)
    write_upstream_ref(
        evidence_dir(args.evidence_dir),
        args.upstream_repository,
        args.upstream_ref,
        resolved,
    )
    print(f"upstream-ref: ok ({resolved})")
    return 0


def cmd_write_image_pipeline(args: argparse.Namespace) -> int:
    write_image_pipeline(
        evidence_dir(args.evidence_dir),
        args.upstream_repository,
        args.upstream_ref,
        args.resolved_revision,
        args.image_name,
        args.image_tag,
        args.platform,
    )
    print(f"image-pipeline: pass ({args.image_name}:{args.image_tag})")
    return 0


def cmd_write_published_image(args: argparse.Namespace) -> int:
    write_published_image(
        evidence_dir(args.evidence_dir),
        args.image_ref,
        args.published_ref,
        args.upstream_repository,
        args.upstream_ref,
        args.resolved_revision,
    )
    print(f"published-image: ok ({args.published_ref})")
    return 0


def cmd_upstream_health(args: argparse.Namespace) -> int:
    report = write_upstream_health(
        args.upstream_repository,
        args.upstream_ref,
        evidence_dir(args.evidence_dir),
        root_dir() / "policies/upstream-health.yml",
        args.mode,
        os.environ.get("GITHUB_TOKEN"),
        args.provider,
        Path(args.signal_file) if args.signal_file else None,
        args.resolved_revision,
    )
    print(f"upstream-health: {report.decision.state} ({report.decision.reason})")
    return 1 if report.decision.blocking else 0


def cmd_public_hygiene(args: argparse.Namespace) -> int:
    report = scan_public_hygiene(
        root_dir(),
        root_dir() / "policies/public-hygiene.yml",
        evidence_dir(args.evidence_dir),
    )
    print(f"public-hygiene: {report.status}")
    return 1 if report.status == "fail" else 0


def cmd_release_check(args: argparse.Namespace) -> int:
    evidence = evidence_dir(args.evidence_dir)
    upstream_repository = getattr(args, "upstream_repository", None) or getattr(
        args, "awx_repo", DEFAULT_AWX_REPO
    )
    upstream_ref = getattr(args, "upstream_ref", None) or getattr(args, "awx_ref", DEFAULT_AWX_REF)
    hygiene = scan_public_hygiene(
        root_dir(),
        root_dir() / "policies/public-hygiene.yml",
        evidence,
    )
    upstream = write_upstream_health(
        upstream_repository,
        upstream_ref,
        evidence,
        root_dir() / "policies/upstream-health.yml",
        "publication",
        os.environ.get("GITHUB_TOKEN"),
        getattr(args, "provider", "auto"),
        Path(args.signal_file) if getattr(args, "signal_file", None) else None,
        getattr(args, "resolved_revision", None),
    )
    failed = hygiene.status == "fail" or upstream.decision.blocking
    status = "fail" if failed else "pass"
    public_hygiene_reason = (
        "Public hygiene passed." if hygiene.status != "fail" else "Public hygiene failed."
    )
    upstream_health_reason = upstream.decision.reason
    reason_parts = []
    if hygiene.status == "fail":
        reason_parts.append(public_hygiene_reason)
    if upstream.decision.blocking:
        reason_parts.append(upstream_health_reason)
    reason = " ".join(reason_parts) if reason_parts else "Release checks passed."
    data = {
        "schema_version": "awx-docker.release-check/v1",
        "status": status,
        "reason": reason,
        "checks": {
            "public_hygiene": hygiene.status,
            "public_hygiene_reason": public_hygiene_reason,
            "upstream_health": upstream.decision.state,
            "upstream_health_reason": upstream_health_reason,
        },
    }
    write_json(evidence / "release-check.json", data)
    write_markdown(
        evidence / "release-check.md",
        "Release Check",
        {
            "status": f"`{status}`",
            "reason": reason,
            "public_hygiene": f"`{hygiene.status}`",
            "public_hygiene_reason": public_hygiene_reason,
            "upstream_health": f"`{upstream.decision.state}`",
            "upstream_health_reason": upstream_health_reason,
        },
    )
    print(f"release-check: {status} ({reason})")
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="awx-docker")
    sub = parser.add_subparsers(required=True)

    resolve = sub.add_parser("resolve-ref")
    resolve.add_argument("--awx-repo", default=os.environ.get("AWX_REPO", DEFAULT_AWX_REPO))
    resolve.add_argument("--awx-ref", default=os.environ.get("AWX_REF", DEFAULT_AWX_REF))
    resolve.set_defaults(func=cmd_resolve_ref)

    metadata = sub.add_parser("write-metadata")
    metadata.add_argument("--awx-repo", default=os.environ.get("AWX_REPO", DEFAULT_AWX_REPO))
    metadata.add_argument("--awx-ref", default=os.environ.get("AWX_REF", DEFAULT_AWX_REF))
    metadata.add_argument("--awx-requested-ref", default=os.environ.get("AWX_REQUESTED_REF"))
    metadata.add_argument("--awx-resolved-ref", default=os.environ.get("AWX_RESOLVED_REF"))
    metadata.add_argument("--image-name", default=os.environ.get("IMAGE_NAME", DEFAULT_IMAGE_NAME))
    metadata.add_argument("--image-tag", default=os.environ.get("IMAGE_TAG", DEFAULT_IMAGE_TAG))
    metadata.add_argument("--platform", default=os.environ.get("PLATFORM", DEFAULT_PLATFORM))
    metadata.add_argument("--evidence-dir", default=os.environ.get("EVIDENCE_DIR"))
    metadata.set_defaults(func=cmd_write_metadata)

    upstream_ref = sub.add_parser("write-upstream-ref")
    upstream_ref.add_argument(
        "--upstream-repository",
        default=os.environ.get("UPSTREAM_REPOSITORY", os.environ.get("AWX_REPO", DEFAULT_AWX_REPO)),
    )
    upstream_ref.add_argument(
        "--upstream-ref",
        default=os.environ.get("UPSTREAM_REF", os.environ.get("AWX_REF", DEFAULT_AWX_REF)),
    )
    upstream_ref.add_argument(
        "--resolved-revision",
        default=os.environ.get("UPSTREAM_RESOLVED_REVISION"),
    )
    upstream_ref.add_argument("--evidence-dir", default=os.environ.get("EVIDENCE_DIR"))
    upstream_ref.set_defaults(func=cmd_write_upstream_ref)

    pipeline = sub.add_parser("write-image-pipeline")
    pipeline.add_argument(
        "--upstream-repository",
        default=os.environ.get("UPSTREAM_REPOSITORY", os.environ.get("AWX_REPO", DEFAULT_AWX_REPO)),
    )
    pipeline.add_argument(
        "--upstream-ref",
        default=os.environ.get("UPSTREAM_REF", os.environ.get("AWX_REF", DEFAULT_AWX_REF)),
    )
    pipeline.add_argument(
        "--resolved-revision",
        required=True,
    )
    pipeline.add_argument("--image-name", default=os.environ.get("IMAGE_NAME", DEFAULT_IMAGE_NAME))
    pipeline.add_argument("--image-tag", default=os.environ.get("IMAGE_TAG", DEFAULT_IMAGE_TAG))
    pipeline.add_argument("--platform", default=os.environ.get("PLATFORM", DEFAULT_PLATFORM))
    pipeline.add_argument("--evidence-dir", default=os.environ.get("EVIDENCE_DIR"))
    pipeline.set_defaults(func=cmd_write_image_pipeline)

    published = sub.add_parser("write-published-image")
    published.add_argument(
        "--upstream-repository",
        default=os.environ.get("UPSTREAM_REPOSITORY", os.environ.get("AWX_REPO", DEFAULT_AWX_REPO)),
    )
    published.add_argument(
        "--upstream-ref",
        default=os.environ.get("UPSTREAM_REF", os.environ.get("AWX_REF", DEFAULT_AWX_REF)),
    )
    published.add_argument("--resolved-revision", required=True)
    published.add_argument("--image-ref", required=True)
    published.add_argument("--published-ref", required=True)
    published.add_argument("--evidence-dir", default=os.environ.get("EVIDENCE_DIR"))
    published.set_defaults(func=cmd_write_published_image)

    upstream = sub.add_parser("upstream-health")
    upstream.add_argument(
        "--upstream-repository",
        default=os.environ.get("UPSTREAM_REPOSITORY", os.environ.get("AWX_REPO", DEFAULT_AWX_REPO)),
    )
    upstream.add_argument(
        "--upstream-ref",
        default=os.environ.get("UPSTREAM_REF", os.environ.get("AWX_REF", DEFAULT_AWX_REF)),
    )
    upstream.add_argument("--awx-repo", dest="upstream_repository", help=argparse.SUPPRESS)
    upstream.add_argument("--awx-ref", dest="upstream_ref", help=argparse.SUPPRESS)
    upstream.add_argument("--provider", default=os.environ.get("UPSTREAM_PROVIDER", "auto"))
    upstream.add_argument("--signal-file", default=os.environ.get("UPSTREAM_SIGNAL_FILE"))
    upstream.add_argument(
        "--resolved-revision", default=os.environ.get("UPSTREAM_RESOLVED_REVISION")
    )
    upstream.add_argument(
        "--mode",
        default=os.environ.get("UPSTREAM_HEALTH_MODE", "scheduled-build"),
    )
    upstream.add_argument("--evidence-dir", default=os.environ.get("EVIDENCE_DIR"))
    upstream.set_defaults(func=cmd_upstream_health)

    hygiene = sub.add_parser("public-hygiene")
    hygiene.add_argument("--evidence-dir", default=os.environ.get("EVIDENCE_DIR"))
    hygiene.set_defaults(func=cmd_public_hygiene)

    release = sub.add_parser("release-check")
    release.add_argument(
        "--upstream-repository",
        default=os.environ.get("UPSTREAM_REPOSITORY", os.environ.get("AWX_REPO", DEFAULT_AWX_REPO)),
    )
    release.add_argument(
        "--upstream-ref",
        default=os.environ.get("UPSTREAM_REF", os.environ.get("AWX_REF", DEFAULT_AWX_REF)),
    )
    release.add_argument("--awx-repo", dest="upstream_repository", help=argparse.SUPPRESS)
    release.add_argument("--awx-ref", dest="upstream_ref", help=argparse.SUPPRESS)
    release.add_argument("--provider", default=os.environ.get("UPSTREAM_PROVIDER", "auto"))
    release.add_argument("--signal-file", default=os.environ.get("UPSTREAM_SIGNAL_FILE"))
    release.add_argument(
        "--resolved-revision", default=os.environ.get("UPSTREAM_RESOLVED_REVISION")
    )
    release.add_argument("--evidence-dir", default=os.environ.get("EVIDENCE_DIR"))
    release.set_defaults(func=cmd_release_check)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
