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


def async_functions() -> dict[str, ast.AsyncFunctionDef]:
    tree = ast.parse((ROOT / "src/awx_docker/main.py").read_text())
    return {node.name: node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)}


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
    assert "image_export" in functions
    assert "image_publish" in functions


def test_dagger_evidence_generates_fresh_lightweight_evidence() -> None:
    evidence = public_dagger_functions()["evidence"]
    source = source_for(evidence)

    assert "_prepare_image_source" in source
    assert "_with_public_hygiene_evidence" in source
    assert 'source.directory("build/evidence")' not in source


def test_image_pipeline_resolves_once_and_reuses_revision() -> None:
    pipeline = public_dagger_functions()["image_pipeline"]
    pipeline_source = source_for(pipeline)
    helper_source = source_for(async_functions()["_verified_image"])

    assert "_verified_image" in pipeline_source
    assert helper_source.count("_resolve_upstream_revision") == 1
    assert "_write_upstream_ref" in helper_source
    assert "_with_upstream_health_evidence" in helper_source
    assert "_write_metadata" in helper_source
    assert "_build_image_from_source" in helper_source
    assert "_write_image_pipeline" in pipeline_source
    assert "resolved_sha" in helper_source


def test_image_publish_requires_publication_gate_by_default() -> None:
    publish = public_dagger_functions()["image_publish"]
    source = source_for(publish)

    assert "publication_gate_override" in source
    assert "_with_publication_gate_evidence" in source
    assert "_write_published_image" in source
    assert ".publish(image_ref)" in source
