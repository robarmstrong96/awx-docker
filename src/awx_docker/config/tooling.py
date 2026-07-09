"""Local tooling settings from the component manifest."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolingSettings:
    """Local tooling versions used by Dagger checks.

    Attributes
    ----------
    python : str
        Python version used for local checks.
    uv_image : str
        Container image that provides uv for Dagger checks.
    """

    python: str
    uv_image: str
