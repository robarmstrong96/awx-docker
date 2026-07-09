"""AWX execution environment settings from the component manifest."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AwxEeSettings:
    """Defaults for the starter AWX execution environment image.

    Attributes
    ----------
    base : str
        Base execution environment image.
    name : str
        Default image name for the built EE image.
    tag : str
        Default image tag for the built EE image.
    platform : str
        Default target container platform.
    """

    base: str
    name: str
    tag: str
    platform: str
