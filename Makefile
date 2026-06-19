.PHONY: check strict-check format lint test upstream-health build verify-image public-readiness publication-gate promote-candidate production-admission production-pipeline evidence help

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
	@dagger call upstream-health --source=. --upstream-ref="$${UPSTREAM_REF:-devel}" --provider="$${UPSTREAM_PROVIDER:-auto}"

build:
	@dagger call image-pipeline --source=. --upstream-ref="$${UPSTREAM_REF:-devel}" --provider="$${UPSTREAM_PROVIDER:-auto}" --image-name="$${IMAGE_NAME:-awx-devel}" --image-tag="$${IMAGE_TAG:-devel}"

verify-image:
	@dagger call image-verify --source=. --awx-ref="$${AWX_REF:-devel}" --image-name="$${IMAGE_NAME:-awx-devel}" --image-tag="$${IMAGE_TAG:-devel}"

public-readiness:
	@dagger call public-readiness --source=.

publication-gate:
	@dagger call publication-gate --source=. --upstream-ref="$${UPSTREAM_REF:-devel}" --provider="$${UPSTREAM_PROVIDER:-auto}"

promote-candidate:
	@dagger call promote-candidate --source=. --upstream-ref="$${UPSTREAM_REF:-devel}" --provider="$${UPSTREAM_PROVIDER:-auto}" --image-name="$${IMAGE_NAME:-awx-devel}" --image-tag="$${IMAGE_TAG:-devel}"

production-admission:
	@dagger call production-admission --source=. --provider="$${UPSTREAM_PROVIDER:-auto}"

production-pipeline:
	@dagger call production-pipeline --source=. --provider="$${UPSTREAM_PROVIDER:-auto}"

evidence:
	@dagger call evidence --source=.
