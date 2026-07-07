import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_contract_module() -> object:
    path = ROOT / "docker/awx/bin/verify-awx-python-contract"
    loader = importlib.machinery.SourceFileLoader("verify_awx_python_contract", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)

    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_awx_manage_entry_point_check_accepts_console_script() -> None:
    contract = load_contract_module()
    dist = SimpleNamespace(
        entry_points=[
            SimpleNamespace(group="console_scripts", name="awx-manage"),
        ]
    )

    contract.check_awx_manage_entry_point(dist)


def test_awx_manage_entry_point_check_rejects_missing_console_script() -> None:
    contract = load_contract_module()
    dist = SimpleNamespace(entry_points=[])

    with pytest.raises(RuntimeError, match="awx-manage"):
        contract.check_awx_manage_entry_point(dist)


def test_awx_version_check_accepts_non_empty_version() -> None:
    contract = load_contract_module()

    contract.check_awx_version_available(SimpleNamespace(__version__="1.0.0"))


def test_awx_version_check_rejects_missing_version() -> None:
    contract = load_contract_module()

    with pytest.raises(RuntimeError, match="__version__"):
        contract.check_awx_version_available(SimpleNamespace())


def test_awx_module_import_check_returns_imported_module(monkeypatch: pytest.MonkeyPatch) -> None:
    contract = load_contract_module()
    awx_module = SimpleNamespace(__version__="1.0.0")
    monkeypatch.setitem(sys.modules, "awx", awx_module)

    assert contract.check_awx_module_importable() is awx_module
