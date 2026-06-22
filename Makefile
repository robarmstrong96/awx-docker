.PHONY: check strict-check format lint test clean distclean upstream-health build public-readiness publication-gate promote-candidate production-admission production-pipeline production-publish help

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

clean:
	@rm -rf build .pytest_cache .ruff_cache
	@find . \( -path ./.git -o -path ./.venv -o -path ./build \) -prune -o -type d -name __pycache__ -exec rm -rf {} +

distclean: clean
	@rm -rf .venv

upstream-health:
	@dagger call upstream-health --source=. --upstream-ref="$${UPSTREAM_REF:-devel}" --provider="$${UPSTREAM_PROVIDER:-auto}"

build:
	@dagger call image-pipeline --source=. --upstream-ref="$${UPSTREAM_REF:-devel}" --provider="$${UPSTREAM_PROVIDER:-auto}" --image-name="$${IMAGE_NAME:-awx-devel}" --image-tag="$${IMAGE_TAG:-devel}"

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

production-publish:
	@dagger call production-publish --source=. --provider="$${UPSTREAM_PROVIDER:-auto}" --registry-username="$${REGISTRY_USERNAME:-}" --registry-token=env://REGISTRY_TOKEN
