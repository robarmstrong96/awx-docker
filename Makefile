.PHONY: check format lint test build verify export clean distclean help

help:
	@dagger functions

check:
	@dagger call check --source=.

format:
	@dagger call format --source=.

lint:
	@dagger call lint --source=.

test:
	@dagger call test --source=.

build:
	@dagger call build --source=. --upstream-ref="$${UPSTREAM_REF:-devel}" --image-name="$${IMAGE_NAME:-awx-devel}" --image-tag="$${IMAGE_TAG:-devel}"

verify:
	@dagger call verify --source=. --upstream-ref="$${UPSTREAM_REF:-devel}" --image-name="$${IMAGE_NAME:-awx-devel}" --image-tag="$${IMAGE_TAG:-devel}" export --path=build/evidence

export:
	@dagger call export --source=. --upstream-ref="$${UPSTREAM_REF:-devel}" --image-ref="$${IMAGE_REF:-awx-devel:devel}" export --path="$${OUTPUT:-build/out/awx-devel.tar}"

clean:
	@rm -rf build .pytest_cache .ruff_cache
	@find . \( -path ./.git -o -path ./.venv -o -path ./build \) -prune -o -type d -name __pycache__ -exec rm -rf {} +

distclean: clean
	@rm -rf .venv
