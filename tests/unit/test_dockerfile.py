from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "docker/awx/Dockerfile"


def dockerfile_text() -> str:
    return DOCKERFILE.read_text()


def test_dockerfile_uses_single_centos_stream_arg() -> None:
    dockerfile = dockerfile_text()

    assert "ARG CENTOS_STREAM_IMAGE=quay.io/centos/centos:stream9" in dockerfile
    assert "FROM quay.io/centos/centos:stream9" not in dockerfile
    assert dockerfile.count("FROM ${CENTOS_STREAM_IMAGE}") == 4


def test_dockerfile_redeclares_only_used_final_stage_args() -> None:
    dockerfile = dockerfile_text()
    final_stage = dockerfile.split("FROM ${CENTOS_STREAM_IMAGE}")[-1]

    assert "ARG AWX_REF\n" not in final_stage
    assert "ARG RECEPTOR_IMAGE\n" in final_stage
    assert 'dev.awx-wrapper.receptor.image="${RECEPTOR_IMAGE}"' in final_stage


def test_dockerfile_groups_runtime_environment() -> None:
    dockerfile = dockerfile_text()

    assert "ENV LANG=en_US.UTF-8 \\\n    LANGUAGE=en_US:en" in dockerfile
    assert dockerfile.count("ENV LANG=en_US.UTF-8") == 2


def test_dockerfile_does_not_use_remote_add_for_repo_files() -> None:
    dockerfile = dockerfile_text()

    assert "ADD https://" not in dockerfile
    assert (
        "COPY docker/awx/repos/ansible-rsyslog-epel-9.repo "
        "/etc/yum.repos.d/ansible-Rsyslog-epel-9.repo"
    ) in dockerfile


def test_rsyslog_repo_file_is_checked_in() -> None:
    repo_file = ROOT / "docker/awx/repos/ansible-rsyslog-epel-9.repo"

    assert repo_file.exists()
    assert "baseurl=https://download.copr.fedorainfracloud.org" in repo_file.read_text()
