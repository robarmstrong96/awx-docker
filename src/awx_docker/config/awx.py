"""AWX source settings from the component manifest."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AwxSource:
    """Upstream AWX repository and ref to build.

    Attributes
    ----------
    repository : str
        Git repository used for AWX source.
    ref : str
        Branch, tag, or commit SHA requested from the repository.
    """

    repository: str
    ref: str
