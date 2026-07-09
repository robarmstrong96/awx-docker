"""AWX source settings from the component manifest."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AwxSource:
    """Upstream AWX repository and ref to build."""

    repository: str
    ref: str
