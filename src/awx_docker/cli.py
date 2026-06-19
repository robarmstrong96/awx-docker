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


def cmd_upstream_health(args: argparse.Namespace) -> int:
    report = write_upstream_health(
        args.awx_repo,
        args.awx_ref,
        evidence_dir(args.evidence_dir),
        root_dir() / "policies/upstream-health.yml",
        args.mode,
        os.environ.get("GITHUB_TOKEN"),
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
    hygiene = scan_public_hygiene(
        root_dir(),
        root_dir() / "policies/public-hygiene.yml",
        evidence,
    )
    upstream = write_upstream_health(
        args.awx_repo,
        args.awx_ref,
        evidence,
        root_dir() / "policies/upstream-health.yml",
        "publication",
        os.environ.get("GITHUB_TOKEN"),
    )
    failed = hygiene.status == "fail" or upstream.decision.blocking
    status = "fail" if failed else "pass"
    data = {
        "schema_version": "awx-docker.release-check/v1",
        "status": status,
        "checks": {
            "public_hygiene": hygiene.status,
            "upstream_health": upstream.decision.state,
        },
    }
    write_json(evidence / "release-check.json", data)
    write_markdown(
        evidence / "release-check.md",
        "Release Check",
        {
            "status": f"`{status}`",
            "public_hygiene": f"`{hygiene.status}`",
            "upstream_health": f"`{upstream.decision.state}`",
        },
    )
    print(f"release-check: {status}")
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

    upstream = sub.add_parser("upstream-health")
    upstream.add_argument("--awx-repo", default=os.environ.get("AWX_REPO", DEFAULT_AWX_REPO))
    upstream.add_argument("--awx-ref", default=os.environ.get("AWX_REF", DEFAULT_AWX_REF))
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
    release.add_argument("--awx-repo", default=os.environ.get("AWX_REPO", DEFAULT_AWX_REPO))
    release.add_argument("--awx-ref", default=os.environ.get("AWX_REF", DEFAULT_AWX_REF))
    release.add_argument("--evidence-dir", default=os.environ.get("EVIDENCE_DIR"))
    release.set_defaults(func=cmd_release_check)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
