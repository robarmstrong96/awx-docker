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
	@dagger call build --source=. --upstream-ref="$${UPSTREAM_REF:-devel}" --awx-ui-repository="$${AWX_UI_REPO:-https://github.com/ansible/ansible-ui.git}" --awx-ui-ref="$${AWX_UI_REF:-v2.4.313}" --image-name="$${IMAGE_NAME:-awx-devel}" --image-tag="$${IMAGE_TAG:-devel}"

verify:
	@dagger call verify --source=. --upstream-ref="$${UPSTREAM_REF:-devel}" --awx-ui-repository="$${AWX_UI_REPO:-https://github.com/ansible/ansible-ui.git}" --awx-ui-ref="$${AWX_UI_REF:-v2.4.313}" --image-name="$${IMAGE_NAME:-awx-devel}" --image-tag="$${IMAGE_TAG:-devel}" export --path=build/evidence

export:
	@dagger call export --source=. --upstream-ref="$${UPSTREAM_REF:-devel}" --awx-ui-repository="$${AWX_UI_REPO:-https://github.com/ansible/ansible-ui.git}" --awx-ui-ref="$${AWX_UI_REF:-v2.4.313}" --image-ref="$${IMAGE_REF:-awx-devel:devel}" export --path="$${OUTPUT:-build/out/awx-devel.tar}"

clean:
	@rm -rf build .pytest_cache .ruff_cache
	@find . \( -path ./.git -o -path ./.venv -o -path ./build \) -prune -o -type d -name __pycache__ -exec rm -rf {} +

distclean: clean
	@rm -rf .venv
