from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_entrypoint_clears_stale_podman_run_state_before_migrate() -> None:
    entrypoint = (ROOT / "scripts/runtime-entrypoint.sh").read_text()

    cleanup = entrypoint.index("reset_podman_run_state")
    cleanup_call = entrypoint.index("reset_podman_run_state\npodman system migrate")

    assert cleanup < cleanup_call
    assert "/run/containers/storage" in entrypoint
    assert "/run/libpod" in entrypoint


def test_scripts_do_not_embed_large_heredocs() -> None:
    script_paths = [
        ROOT / "scripts/runtime-entrypoint.sh",
        ROOT / "docker/awx/bin/verify-runtime-contract",
    ]

    for path in script_paths:
        assert "<<" not in path.read_text(), f"{path} should use tracked helper files"
