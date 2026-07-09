"""Local tooling settings from the component manifest."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolingSettings:
    """Local tooling versions used by Dagger checks."""

    python: str
    uv_image: str
