import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def public_dagger_functions() -> dict[str, ast.AsyncFunctionDef]:
    tree = ast.parse((ROOT / "src/awx_docker/main.py").read_text())
    functions = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        if any(
            isinstance(decorator, ast.Name) and decorator.id == "function"
            for decorator in node.decorator_list
        ):
            functions[node.name] = node
    return functions


def source_for(function: ast.AsyncFunctionDef) -> str:
    return ast.unparse(function)


def test_dagger_public_surface_is_small_and_documented() -> None:
    functions = public_dagger_functions()

    assert set(functions) == {
        "check",
        "evidence",
        "format",
        "image_build",
        "image_verify",
        "lint",
        "public_hygiene",
        "release_check",
        "resolve_ref",
        "test",
        "upstream_health",
    }
    for function in functions.values():
        assert ast.get_docstring(function)


def test_dagger_evidence_generates_fresh_lightweight_evidence() -> None:
    evidence = public_dagger_functions()["evidence"]
    source = source_for(evidence)

    assert "_prepare_image_source" in source
    assert "_with_public_hygiene_evidence" in source
    assert 'source.directory("build/evidence")' not in source
