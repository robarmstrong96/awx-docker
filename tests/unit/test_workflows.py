from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"


def workflow(path: str) -> dict:
    return yaml.safe_load((WORKFLOWS / path).read_text())


def test_named_workflow_files_replace_old_graph() -> None:
    assert not (WORKFLOWS / "check.yml").exists()
    assert not (WORKFLOWS / "image-build.yml").exists()
    assert (WORKFLOWS / "project-checks.yml").exists()
    assert (WORKFLOWS / "image-pipeline.yml").exists()
    assert (WORKFLOWS / "production-admission.yml").exists()
    assert (WORKFLOWS / "production-pipeline.yml").exists()
    assert (WORKFLOWS / "publication-gate.yml").exists()


def test_workflow_and_job_names_are_presentable() -> None:
    assert workflow("project-checks.yml")["name"] == "Project Checks"
    assert workflow("image-pipeline.yml")["name"] == "Image Pipeline"
    assert workflow("production-admission.yml")["name"] == "Production Admission"
    assert workflow("production-pipeline.yml")["name"] == "Production Pipeline"
    assert workflow("publication-gate.yml")["name"] == "Publication Gate"

    admission_jobs = workflow("production-admission.yml")["jobs"]
    assert admission_jobs["validate-production-lock"]["name"] == "Validate production lock"
    assert admission_jobs["publication-gate"]["name"] == "Publication gate"


def test_dagger_workflows_use_pinned_engine_version() -> None:
    for path in WORKFLOWS.glob("*.yml"):
        data = workflow(path.name)
        for job in data["jobs"].values():
            for step in job["steps"]:
                if step.get("uses") == "dagger/dagger-for-github@v8.3.0":
                    assert step["with"]["version"] == "v0.21.4"


def test_evidence_workflows_upload_artifacts() -> None:
    evidence_workflows = [
        "image-pipeline.yml",
        "production-admission.yml",
        "production-pipeline.yml",
        "publication-gate.yml",
    ]

    for name in evidence_workflows:
        data = workflow(name)
        for job in data["jobs"].values():
            upload_steps = [
                step for step in job["steps"] if step.get("uses") == "actions/upload-artifact@v4"
            ]
            assert upload_steps
            assert all(step.get("continue-on-error") is True for step in upload_steps)

    public_readiness = workflow("project-checks.yml")["jobs"]["public-readiness"]
    upload_steps = [
        step
        for step in public_readiness["steps"]
        if step.get("uses") == "actions/upload-artifact@v4"
    ]
    assert upload_steps
    assert all(step.get("continue-on-error") is True for step in upload_steps)
