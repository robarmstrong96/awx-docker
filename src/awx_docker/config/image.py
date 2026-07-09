"""AWX image settings from the component manifest."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ImageSettings:
    """Defaults for the AWX control-plane image build.

    Attributes
    ----------
    base : str
        Base image used by the AWX Dockerfile.
    receptor : str
        Receptor image copied into the AWX image.
    name : str
        Default image name for the built AWX image.
    tag : str
        Default image tag for the built AWX image.
    platform : str
        Default target container platform.
    """

    base: str
    receptor: str
    name: str
    tag: str
    platform: str
