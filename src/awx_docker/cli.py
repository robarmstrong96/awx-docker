import argparse
import os
from pathlib import Path
from types import SimpleNamespace

import yaml

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
from awx_docker.production import (
    build_lock,
    load_lock,
    validate_lock,
    write_lock,
    write_production_admission,
    write_production_pipeline,
    write_promotion_candidate,
)
from awx_docker.production.lock import branch_policy_errors
from awx_docker.public_readiness import scan_public_readiness
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


def cmd_public_readiness(args: argparse.Namespace) -> int:
    report = scan_public_readiness(
        root_dir(),
        root_dir() / "policies/public-readiness.yml",
        evidence_dir(args.evidence_dir),
    )
    print(f"public-readiness: {report.status}")
    return 1 if report.status == "fail" else 0


def run_publication_gate(
    upstream_repository: str,
    upstream_ref: str,
    provider: str,
    signal_file: str | None,
    resolved_revision: str | None,
    evidence: Path,
) -> SimpleNamespace:
    readiness = scan_public_readiness(
        root_dir(),
        root_dir() / "policies/public-readiness.yml",
        evidence,
    )
    upstream = write_upstream_health(
        upstream_repository,
        upstream_ref,
        evidence,
        root_dir() / "policies/upstream-health.yml",
        "publication",
        os.environ.get("GITHUB_TOKEN"),
        provider,
        Path(signal_file) if signal_file else None,
        resolved_revision,
    )
    failed = readiness.status == "fail" or upstream.decision.blocking
    status = "fail" if failed else "pass"
    public_readiness_reason = (
        "Public readiness passed." if readiness.status != "fail" else "Public readiness failed."
    )
    upstream_health_reason = upstream.decision.reason
    reason_parts = []
    if readiness.status == "fail":
        reason_parts.append(public_readiness_reason)
    if upstream.decision.blocking:
        reason_parts.append(upstream_health_reason)
    reason = " ".join(reason_parts) if reason_parts else "Publication gate passed."
    data = {
        "schema_version": "awx-docker.publication-gate/v1",
        "status": status,
        "reason": reason,
        "checks": {
            "public_readiness": readiness.status,
            "public_readiness_reason": public_readiness_reason,
            "upstream_health": upstream.decision.state,
            "upstream_health_reason": upstream_health_reason,
        },
    }
    write_json(evidence / "publication-gate.json", data)
    write_markdown(
        evidence / "publication-gate.md",
        "Publication Gate",
        {
            "status": f"`{status}`",
            "reason": reason,
            "public_readiness": f"`{readiness.status}`",
            "public_readiness_reason": public_readiness_reason,
            "upstream_health": f"`{upstream.decision.state}`",
            "upstream_health_reason": upstream_health_reason,
        },
    )
    return SimpleNamespace(
        status=status,
        reason=reason,
        public_readiness_status=readiness.status,
        upstream_health_status=upstream.decision.state,
        upstream_health_blocking=upstream.decision.blocking,
    )


def cmd_publication_gate(args: argparse.Namespace) -> int:
    evidence = evidence_dir(args.evidence_dir)
    upstream_repository = getattr(args, "upstream_repository", None) or getattr(
        args, "awx_repo", DEFAULT_AWX_REPO
    )
    upstream_ref = getattr(args, "upstream_ref", None) or getattr(args, "awx_ref", DEFAULT_AWX_REF)
    gate = run_publication_gate(
        upstream_repository,
        upstream_ref,
        getattr(args, "provider", "auto"),
        getattr(args, "signal_file", None),
        getattr(args, "resolved_revision", None),
        evidence,
    )
    print(f"publication-gate: {gate.status} ({gate.reason})")
    return 1 if gate.status == "fail" else 0


def cmd_promote_candidate(args: argparse.Namespace) -> int:
    resolved = args.resolved_revision or resolve_ref(args.upstream_repository, args.upstream_ref)
    lock = build_lock(
        args.upstream_repository,
        args.upstream_ref,
        resolved,
        args.image_name,
        args.image_tag,
        evidence_run_url=args.evidence_run_url,
        promoted_by=args.promoted_by,
        notes=args.notes,
    )
    errors = validate_lock(lock)
    if errors:
        print(f"promote-candidate: fail ({'; '.join(errors)})")
        return 1
    write_lock(root_dir() / "awx.lock.yml", lock)
    write_promotion_candidate(evidence_dir(args.evidence_dir), lock)
    print(f"promote-candidate: pass ({resolved})")
    return 0


def cmd_production_admission(args: argparse.Namespace) -> int:
    evidence = evidence_dir(args.evidence_dir)
    lock_path = root_dir() / "awx.lock.yml"
    lock_present = lock_path.exists()
    lock_errors = []
    lock = None
    if lock_present:
        lock = load_lock(lock_path)
        lock_errors = validate_lock(lock)
    else:
        lock_errors = ["awx.lock.yml is missing"]

    policy = yaml.safe_load((root_dir() / "policies/branches.yml").read_text())
    branch_errors = branch_policy_errors(policy, "production", lock_present)
    if lock is None or lock_errors:
        readiness = scan_public_readiness(
            root_dir(),
            root_dir() / "policies/public-readiness.yml",
            evidence,
        )
        gate = SimpleNamespace(
            status="fail",
            reason="awx.lock.yml is missing or invalid.",
            public_readiness_status=readiness.status,
        )
    else:
        gate = run_publication_gate(
            lock["upstream"]["repository"],
            lock["upstream"]["requested_ref"],
            args.provider,
            args.signal_file,
            lock["upstream"]["resolved_revision"],
            evidence,
        )

    report = write_production_admission(
        evidence,
        lock_present=lock_present,
        lock_errors=lock_errors,
        branch_errors=branch_errors,
        public_readiness_status=gate.public_readiness_status,
        publication_gate_status=gate.status,
        publication_gate_reason=gate.reason,
    )
    print(f"production-admission: {report['status']} ({report['reason']})")
    return 1 if report["status"] == "fail" else 0


def cmd_write_production_pipeline(args: argparse.Namespace) -> int:
    lock = load_lock(root_dir() / "awx.lock.yml")
    errors = validate_lock(lock)
    if errors:
        print(f"production-pipeline: fail ({'; '.join(errors)})")
        return 1
    write_production_pipeline(evidence_dir(args.evidence_dir), lock)
    print(f"production-pipeline: pass ({lock['upstream']['resolved_revision']})")
    return 0


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

    readiness = sub.add_parser("public-readiness")
    readiness.add_argument("--evidence-dir", default=os.environ.get("EVIDENCE_DIR"))
    readiness.set_defaults(func=cmd_public_readiness)

    publication = sub.add_parser("publication-gate")
    publication.add_argument(
        "--upstream-repository",
        default=os.environ.get("UPSTREAM_REPOSITORY", os.environ.get("AWX_REPO", DEFAULT_AWX_REPO)),
    )
    publication.add_argument(
        "--upstream-ref",
        default=os.environ.get("UPSTREAM_REF", os.environ.get("AWX_REF", DEFAULT_AWX_REF)),
    )
    publication.add_argument("--awx-repo", dest="upstream_repository", help=argparse.SUPPRESS)
    publication.add_argument("--awx-ref", dest="upstream_ref", help=argparse.SUPPRESS)
    publication.add_argument("--provider", default=os.environ.get("UPSTREAM_PROVIDER", "auto"))
    publication.add_argument("--signal-file", default=os.environ.get("UPSTREAM_SIGNAL_FILE"))
    publication.add_argument(
        "--resolved-revision", default=os.environ.get("UPSTREAM_RESOLVED_REVISION")
    )
    publication.add_argument("--evidence-dir", default=os.environ.get("EVIDENCE_DIR"))
    publication.set_defaults(func=cmd_publication_gate)

    promote = sub.add_parser("promote-candidate")
    promote.add_argument(
        "--upstream-repository",
        default=os.environ.get("UPSTREAM_REPOSITORY", os.environ.get("AWX_REPO", DEFAULT_AWX_REPO)),
    )
    promote.add_argument(
        "--upstream-ref",
        default=os.environ.get("UPSTREAM_REF", os.environ.get("AWX_REF", DEFAULT_AWX_REF)),
    )
    promote.add_argument(
        "--resolved-revision", default=os.environ.get("UPSTREAM_RESOLVED_REVISION")
    )
    promote.add_argument("--image-name", default=os.environ.get("IMAGE_NAME", DEFAULT_IMAGE_NAME))
    promote.add_argument("--image-tag", default=os.environ.get("IMAGE_TAG", DEFAULT_IMAGE_TAG))
    promote.add_argument("--promoted-by", default=os.environ.get("PROMOTED_BY", ""))
    promote.add_argument("--evidence-run-url", default=os.environ.get("EVIDENCE_RUN_URL", ""))
    promote.add_argument("--notes", default=os.environ.get("PROMOTION_NOTES", ""))
    promote.add_argument("--evidence-dir", default=os.environ.get("EVIDENCE_DIR"))
    promote.set_defaults(func=cmd_promote_candidate)

    admission = sub.add_parser("production-admission")
    admission.add_argument("--provider", default=os.environ.get("UPSTREAM_PROVIDER", "auto"))
    admission.add_argument("--signal-file", default=os.environ.get("UPSTREAM_SIGNAL_FILE"))
    admission.add_argument("--evidence-dir", default=os.environ.get("EVIDENCE_DIR"))
    admission.set_defaults(func=cmd_production_admission)

    production = sub.add_parser("write-production-pipeline")
    production.add_argument("--evidence-dir", default=os.environ.get("EVIDENCE_DIR"))
    production.set_defaults(func=cmd_write_production_pipeline)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
