.PHONY: check strict-check format lint test upstream-health build verify-image public-readiness publication-gate evidence help

help:
	@dagger functions

check:
	@dagger call check --source=.

strict-check:
	@dagger call strict-check --source=.

format:
	@dagger call format --source=.

lint:
	@dagger call lint --source=.

test:
	@dagger call test --source=.

upstream-health:
	@dagger call upstream-health --source=. --awx-ref="$${AWX_REF:-devel}"

build:
	@dagger call image-build --source=. --awx-ref="$${AWX_REF:-devel}" --image-name="$${IMAGE_NAME:-awx-devel}" --image-tag="$${IMAGE_TAG:-devel}"

verify-image:
	@dagger call image-verify --source=. --awx-ref="$${AWX_REF:-devel}" --image-name="$${IMAGE_NAME:-awx-devel}" --image-tag="$${IMAGE_TAG:-devel}"

public-readiness:
	@dagger call public-readiness --source=.

publication-gate:
	@dagger call publication-gate --source=. --awx-ref="$${AWX_REF:-devel}"

evidence:
	@dagger call evidence --source=.
