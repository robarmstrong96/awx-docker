import argparse
import json
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

PUBLICATION_PURPOSES = {
    "repository",
    "image-publication",
    "production-admission",
    "production-promotion",
}


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
    purpose: str = "repository",
) -> SimpleNamespace:
    policy = yaml.safe_load((root_dir() / "policies/image-publication.yml").read_text())
    required_checks = required_publication_checks(policy, purpose)
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
    image_status, image_reason = image_verification_check(
        evidence, required="image-verification" in required_checks
    )
    upstream_health_reason = upstream.decision.reason
    missing_required = missing_publication_evidence(
        required_checks,
        readiness.status,
        upstream.decision.blocking,
        upstream_health_reason,
        image_status,
        image_reason,
    )
    failed = bool(missing_required)
    status = "fail" if failed else "pass"
    public_readiness_reason = (
        "Public readiness passed." if readiness.status != "fail" else "Public readiness failed."
    )
    reason_parts = missing_required
    reason = " ".join(reason_parts) if reason_parts else "Publication gate passed."
    write_publication_gate_report(
        evidence,
        purpose,
        policy.get("schema", ""),
        required_checks,
        status,
        reason,
        {
            "public_readiness": readiness.status,
            "public_readiness_reason": public_readiness_reason,
            "upstream_health": upstream.decision.state,
            "upstream_health_reason": upstream_health_reason,
            "image_verification": image_status,
            "image_verification_reason": image_reason,
        },
    )
    return SimpleNamespace(
        status=status,
        reason=reason,
        public_readiness_status=readiness.status,
        upstream_health_status=upstream.decision.state,
        upstream_health_blocking=upstream.decision.blocking,
        image_verification_status=image_status,
    )


def cmd_publication_gate(args: argparse.Namespace) -> int:
    evidence = evidence_dir(args.evidence_dir)
    purpose = getattr(args, "purpose", "repository")
    if purpose not in PUBLICATION_PURPOSES:
        print(f"publication-gate: fail (unknown publication purpose: {purpose})")
        return 1
    if getattr(args, "from_lock", False):
        try:
            lock = load_lock(root_dir() / "awx.lock.yml")
        except FileNotFoundError:
            lock = None
            lock_errors = ["awx.lock.yml is missing"]
        else:
            lock_errors = validate_lock(
                lock,
                require_promotion_evidence=purpose.startswith("production"),
            )
        if lock_errors:
            policy = yaml.safe_load((root_dir() / "policies/image-publication.yml").read_text())
            required_checks = required_publication_checks(policy, purpose)
            reason = "; ".join(lock_errors)
            write_publication_gate_report(
                evidence,
                purpose,
                policy.get("schema", ""),
                required_checks,
                "fail",
                reason,
                {
                    "lock_file": "fail",
                    "lock_file_reason": reason,
                    "public_readiness": "not_run",
                    "public_readiness_reason": "Lock validation failed.",
                    "upstream_health": "not_run",
                    "upstream_health_reason": "Lock validation failed.",
                    "image_verification": "not_required",
                    "image_verification_reason": (
                        "Image verification is not required for this gate."
                    ),
                },
            )
            print(f"publication-gate: fail ({reason})")
            return 1
        assert lock is not None
        upstream_repository = lock["upstream"]["repository"]
        upstream_ref = lock["upstream"]["requested_ref"]
        resolved_revision = lock["upstream"]["resolved_revision"]
    else:
        upstream_repository = getattr(args, "upstream_repository", DEFAULT_AWX_REPO)
        upstream_ref = getattr(args, "upstream_ref", DEFAULT_AWX_REF)
        resolved_revision = getattr(args, "resolved_revision", None)
    gate = run_publication_gate(
        upstream_repository,
        upstream_ref,
        getattr(args, "provider", "auto"),
        getattr(args, "signal_file", None),
        resolved_revision,
        evidence,
        purpose,
    )
    print(f"publication-gate: {gate.status} ({gate.reason})")
    return 1 if gate.status == "fail" else 0


def required_publication_checks(policy: dict, purpose: str) -> list[str]:
    context = (policy.get("contexts") or {}).get(purpose)
    if isinstance(context, dict):
        checks = context.get("required_checks", [])
    else:
        checks = policy.get("required_checks", [])
    return [str(check) for check in checks]


def image_verification_check(evidence: Path, *, required: bool) -> tuple[str, str]:
    report_path = evidence / "image-verification.json"
    if not report_path.exists():
        if required:
            return "fail", "image-verification.json is required but was not found."
        return "not_required", "Image verification is not required for this gate."
    try:
        data = json.loads(report_path.read_text())
    except json.JSONDecodeError as exc:
        return "fail", f"image-verification.json is invalid JSON: {exc}"
    if data.get("status") == "passed":
        return "pass", "Image verification passed."
    return "fail", "Image verification did not pass."


def missing_publication_evidence(
    required_checks: list[str],
    public_readiness_status: str,
    upstream_health_blocking: bool,
    upstream_health_reason: str,
    image_verification_status: str,
    image_verification_reason: str,
) -> list[str]:
    failures = []
    if "public-readiness" in required_checks and public_readiness_status == "fail":
        failures.append("Public readiness failed.")
    if "upstream-health" in required_checks and upstream_health_blocking:
        failures.append(upstream_health_reason)
    if "image-verification" in required_checks and image_verification_status != "pass":
        failures.append(image_verification_reason)
    return failures


def write_publication_gate_report(
    evidence: Path,
    purpose: str,
    policy_schema: str,
    required_checks: list[str],
    status: str,
    reason: str,
    checks: dict[str, str | bool],
) -> None:
    data = {
        "schema_version": "awx-docker.publication-gate/v1",
        "status": status,
        "reason": reason,
        "purpose": purpose,
        "policy": {
            "schema": policy_schema,
            "required_checks": required_checks,
        },
        "checks": checks,
    }
    write_json(evidence / "publication-gate.json", data)
    write_markdown(
        evidence / "publication-gate.md",
        "Publication Gate",
        {
            "status": f"`{status}`",
            "purpose": f"`{purpose}`",
            "reason": reason,
            "required_checks": ", ".join(required_checks),
            **{key: value for key, value in checks.items() if key.endswith("_reason")},
        },
    )


def cmd_promote_candidate(args: argparse.Namespace) -> int:
    resolved = args.resolved_revision or resolve_ref(args.upstream_repository, args.upstream_ref)
    lock = build_lock(
        args.upstream_repository,
        args.upstream_ref,
        resolved,
        args.image_name,
        args.image_tag,
        evidence_run_url=args.evidence_run_url,
        evidence_waiver=args.evidence_waiver,
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
        lock_errors = validate_lock(lock, require_promotion_evidence=True)
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
            "production-admission",
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
    errors = validate_lock(lock, require_promotion_evidence=True)
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
    resolve.add_argument(
        "--upstream-repository",
        default=os.environ.get("UPSTREAM_REPOSITORY", os.environ.get("AWX_REPO", DEFAULT_AWX_REPO)),
    )
    resolve.add_argument(
        "--upstream-ref",
        default=os.environ.get("UPSTREAM_REF", os.environ.get("AWX_REF", DEFAULT_AWX_REF)),
    )
    resolve.add_argument("--awx-repo", dest="upstream_repository", help=argparse.SUPPRESS)
    resolve.add_argument("--awx-ref", dest="upstream_ref", help=argparse.SUPPRESS)
    resolve.set_defaults(func=cmd_resolve_ref)

    metadata = sub.add_parser("write-metadata")
    metadata.add_argument(
        "--upstream-repository",
        default=os.environ.get("UPSTREAM_REPOSITORY", os.environ.get("AWX_REPO", DEFAULT_AWX_REPO)),
    )
    metadata.add_argument(
        "--upstream-ref",
        default=os.environ.get("UPSTREAM_REF", os.environ.get("AWX_REF", DEFAULT_AWX_REF)),
    )
    metadata.add_argument(
        "--upstream-requested-ref",
        default=os.environ.get("UPSTREAM_REQUESTED_REF", os.environ.get("AWX_REQUESTED_REF")),
    )
    metadata.add_argument(
        "--upstream-resolved-revision",
        default=os.environ.get("UPSTREAM_RESOLVED_REVISION", os.environ.get("AWX_RESOLVED_REF")),
    )
    metadata.add_argument("--awx-repo", dest="upstream_repository", help=argparse.SUPPRESS)
    metadata.add_argument("--awx-ref", dest="upstream_ref", help=argparse.SUPPRESS)
    metadata.add_argument(
        "--awx-requested-ref", dest="upstream_requested_ref", help=argparse.SUPPRESS
    )
    metadata.add_argument(
        "--awx-resolved-ref", dest="upstream_resolved_revision", help=argparse.SUPPRESS
    )
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
    publication.add_argument("--from-lock", action="store_true")
    publication.add_argument(
        "--purpose", default=os.environ.get("PUBLICATION_PURPOSE", "repository")
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
    promote.add_argument("--evidence-waiver", default=os.environ.get("EVIDENCE_WAIVER", ""))
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
