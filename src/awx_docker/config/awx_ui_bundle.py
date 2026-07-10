"""AWX UI bundle settings from the component manifest."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AwxUiBundleSettings:
    """Defaults for the exported static UI bundle.

    Attributes
    ----------
    name : str
        Default image name for the UI bundle image.
    tag : str
        Default image tag for the UI bundle image.
    export_path : str
        Path inside the bundle image containing static files.
    """

    name: str
    tag: str
    export_path: str
