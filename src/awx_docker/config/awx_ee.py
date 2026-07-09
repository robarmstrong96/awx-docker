"""AWX execution environment settings from the component manifest."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AwxEeSettings:
    """Defaults for the starter AWX execution environment image."""

    base: str
    name: str
    tag: str
    platform: str
