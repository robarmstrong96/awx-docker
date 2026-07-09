import importlib.machinery
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_contract_module() -> object:
    path = ROOT / "docker/awx/bin/verify-awx-python-contract"
    loader = importlib.machinery.SourceFileLoader("verify_awx_python_contract", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)

    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_awx_python_contract_helper_imports() -> None:
    contract = load_contract_module()

    assert hasattr(contract, "main")
