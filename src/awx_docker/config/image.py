"""AWX image settings from the component manifest."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ImageSettings:
    """Defaults for the AWX control-plane image build."""

    base: str
    receptor: str
    name: str
    tag: str
    platform: str
