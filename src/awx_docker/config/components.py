"""Combined component settings model."""

from dataclasses import dataclass

from awx_docker.config.awx import AwxSource
from awx_docker.config.awx_ee import AwxEeSettings
from awx_docker.config.awx_ui import AwxUiSource
from awx_docker.config.awx_ui_bundle import AwxUiBundleSettings
from awx_docker.config.image import ImageSettings
from awx_docker.config.python import PythonSettings
from awx_docker.config.tooling import ToolingSettings


@dataclass(frozen=True)
class Components:
    """Typed view of config/components/components.toml."""

    schema_version: int
    awx: AwxSource
    awx_ui: AwxUiSource
    awx_ui_bundle: AwxUiBundleSettings
    awx_ee: AwxEeSettings
    images: ImageSettings
    python: PythonSettings
    tooling: ToolingSettings
