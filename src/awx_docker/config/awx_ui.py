"""AWX UI source settings from the component manifest."""

from dataclasses import dataclass
from enum import StrEnum


class AwxUiDelivery(StrEnum):
    """Supported ways to ship AWX UI static files."""

    EMBEDDED = "embedded"
    SIDELOADED = "sideloaded"


@dataclass(frozen=True)
class AwxUiSource:
    """Pinned AWX UI source and delivery mode."""

    repository: str
    ref: str
    delivery: AwxUiDelivery
