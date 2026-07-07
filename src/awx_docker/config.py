from pathlib import Path

DEFAULT_AWX_REPO = "https://github.com/ansible/awx.git"
DEFAULT_AWX_REF = "devel"
DEFAULT_AWX_UI_REPO = "https://github.com/ansible/ansible-ui.git"
DEFAULT_AWX_UI_REF = "v2.4.313"
DEFAULT_RECEPTOR_IMAGE = "quay.io/ansible/receptor:devel"
DEFAULT_PLATFORM = "linux/amd64"
DEFAULT_EVIDENCE_DIR = Path("build/evidence")
DEFAULT_IMAGE_NAME = "awx-devel"
DEFAULT_IMAGE_TAG = "devel"
