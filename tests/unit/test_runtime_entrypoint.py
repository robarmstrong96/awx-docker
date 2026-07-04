from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_entrypoint_clears_stale_podman_run_state_before_migrate() -> None:
    entrypoint = (ROOT / "scripts/runtime-entrypoint.sh").read_text()

    cleanup = entrypoint.index("reset_podman_run_state")
    cleanup_call = entrypoint.index("reset_podman_run_state\npodman system migrate")

    assert cleanup < cleanup_call
    assert "/run/containers/storage" in entrypoint
    assert "/run/libpod" in entrypoint
