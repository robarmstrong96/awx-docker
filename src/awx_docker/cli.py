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
from awx_docker.git_refs import resolve_ref
from awx_docker.image.metadata import write_build_metadata
from awx_docker.image.pipeline import write_upstream_ref


def root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def evidence_dir(value: str | None = None) -> Path:
    return Path(value or os.environ.get("EVIDENCE_DIR", DEFAULT_EVIDENCE_DIR))


def cmd_resolve_ref(args: argparse.Namespace) -> int:
    print(resolve_ref(args.upstream_repository, args.upstream_ref))
    return 0


def cmd_write_metadata(args: argparse.Namespace) -> int:
    resolved = args.upstream_resolved_revision or resolve_ref(
        args.upstream_repository, args.upstream_ref
    )
    write_build_metadata(
        root_dir(),
        evidence_dir(args.evidence_dir),
        args.image_name,
        args.image_tag,
        args.upstream_repository,
        args.upstream_requested_ref or args.upstream_ref,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="awx-docker")
    sub = parser.add_subparsers(required=True)

    resolver = sub.add_parser("resolve-ref")
    resolver.add_argument(
        "--upstream-repository",
        default=os.environ.get("UPSTREAM_REPOSITORY", DEFAULT_AWX_REPO),
    )
    resolver.add_argument("--upstream-ref", default=os.environ.get("UPSTREAM_REF", DEFAULT_AWX_REF))
    resolver.add_argument("--awx-repo", dest="upstream_repository", help=argparse.SUPPRESS)
    resolver.add_argument("--awx-ref", dest="upstream_ref", help=argparse.SUPPRESS)
    resolver.set_defaults(func=cmd_resolve_ref)

    metadata = sub.add_parser("write-metadata")
    metadata.add_argument(
        "--upstream-repository",
        default=os.environ.get("UPSTREAM_REPOSITORY", DEFAULT_AWX_REPO),
    )
    metadata.add_argument("--upstream-ref", default=os.environ.get("UPSTREAM_REF", DEFAULT_AWX_REF))
    metadata.add_argument(
        "--upstream-requested-ref",
        default=os.environ.get("UPSTREAM_REQUESTED_REF"),
    )
    metadata.add_argument(
        "--upstream-resolved-revision",
        default=os.environ.get("UPSTREAM_RESOLVED_REVISION"),
    )
    metadata.add_argument("--awx-repo", dest="upstream_repository", help=argparse.SUPPRESS)
    metadata.add_argument("--awx-ref", dest="upstream_ref", help=argparse.SUPPRESS)
    metadata.add_argument(
        "--awx-requested-ref", dest="upstream_requested_ref", help=argparse.SUPPRESS
    )
    metadata.add_argument(
        "--awx-resolved-ref",
        dest="upstream_resolved_revision",
        help=argparse.SUPPRESS,
    )
    metadata.add_argument("--image-name", default=os.environ.get("IMAGE_NAME", DEFAULT_IMAGE_NAME))
    metadata.add_argument("--image-tag", default=os.environ.get("IMAGE_TAG", DEFAULT_IMAGE_TAG))
    metadata.add_argument("--platform", default=os.environ.get("PLATFORM", DEFAULT_PLATFORM))
    metadata.add_argument("--evidence-dir", default=os.environ.get("EVIDENCE_DIR"))
    metadata.set_defaults(func=cmd_write_metadata)

    upstream_ref = sub.add_parser("write-upstream-ref")
    upstream_ref.add_argument(
        "--upstream-repository",
        default=os.environ.get("UPSTREAM_REPOSITORY", DEFAULT_AWX_REPO),
    )
    upstream_ref.add_argument(
        "--upstream-ref",
        default=os.environ.get("UPSTREAM_REF", DEFAULT_AWX_REF),
    )
    upstream_ref.add_argument("--resolved-revision", default=os.environ.get("RESOLVED_REVISION"))
    upstream_ref.add_argument("--evidence-dir", default=os.environ.get("EVIDENCE_DIR"))
    upstream_ref.set_defaults(func=cmd_write_upstream_ref)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
