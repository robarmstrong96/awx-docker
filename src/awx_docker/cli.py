"""Command-line helpers used by the Dagger build."""

import argparse
import os

from awx_docker.git_refs import resolve_ref
from awx_docker.utilities.load_configuration import (
    DEFAULT_AWX_REF,
    DEFAULT_AWX_REPO,
)


def cmd_resolve_ref(args: argparse.Namespace) -> int:
    """Print the resolved upstream AWX commit SHA.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed ``resolve-ref`` command arguments.

    Returns
    -------
    int
        Process exit code.
    """
    print(resolve_ref(args.upstream_repository, args.upstream_ref))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the small CLI parser used inside build containers.

    Returns
    -------
    argparse.ArgumentParser
        Parser for the internal ``awx-docker`` CLI.
    """
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

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code.

    Parameters
    ----------
    argv : list[str] | None
        Optional argv list. When omitted, argparse reads from ``sys.argv``.

    Returns
    -------
    int
        Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
