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


def test_dagger_public_functions_are_documented() -> None:
    functions = public_dagger_functions()

    for function in functions.values():
        assert ast.get_docstring(function)


def test_dagger_surface_includes_public_readiness_aliases() -> None:
    functions = public_dagger_functions()

    assert "public_readiness" in functions
    assert "publication_gate" in functions
    assert "image_pipeline" in functions


def test_dagger_evidence_generates_fresh_lightweight_evidence() -> None:
    evidence = public_dagger_functions()["evidence"]
    source = source_for(evidence)

    assert "_prepare_image_source" in source
    assert "_with_public_hygiene_evidence" in source
    assert 'source.directory("build/evidence")' not in source


def test_image_pipeline_resolves_once_and_reuses_revision() -> None:
    pipeline = public_dagger_functions()["image_pipeline"]
    source = source_for(pipeline)

    assert source.count("_resolve_upstream_revision") == 1
    assert "_write_upstream_ref" in source
    assert "_with_upstream_health_evidence" in source
    assert "_write_metadata" in source
    assert "_build_image_from_source" in source
    assert "_write_image_pipeline" in source
    assert "resolved_sha" in source
