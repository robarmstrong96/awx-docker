"""AWX UI source settings from the component manifest."""

from dataclasses import dataclass
from enum import StrEnum


class AwxUiDelivery(StrEnum):
    """Supported ways to ship AWX UI static files.

    Attributes
    ----------
    EMBEDDED : AwxUiDelivery
        Build UI assets into the AWX image.
    SIDELOADED : AwxUiDelivery
        Serve UI assets from a mounted static bundle.
    """

    EMBEDDED = "embedded"
    SIDELOADED = "sideloaded"


@dataclass(frozen=True)
class AwxUiSource:
    """Pinned AWX UI source and delivery mode.

    Attributes
    ----------
    repository : str
        Git repository used for AWX UI source.
    ref : str
        Branch, tag, or commit SHA requested from the repository.
    delivery : AwxUiDelivery
        How the built AWX image should receive UI static files.
    """

    repository: str
    ref: str
    delivery: AwxUiDelivery
