"""Python dependency settings from the component manifest."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PythonSettings:
    """Python dependency knobs owned by this wrapper."""

    constraints: str
