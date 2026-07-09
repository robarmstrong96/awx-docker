"""AWX UI bundle settings from the component manifest."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AwxUiBundleSettings:
    """Defaults for the exported static UI bundle."""

    name: str
    tag: str
    export_path: str
