set shell := ["bash", "-uc"]

upstream_ref := env_var_or_default("UPSTREAM_REF", "devel")
awx_ui_repo := env_var_or_default("AWX_UI_REPO", "https://github.com/ansible/ansible-ui.git")
awx_ui_ref := env_var_or_default("AWX_UI_REF", "v2.4.313")
image_name := env_var_or_default("IMAGE_NAME", "awx-devel")
image_tag := env_var_or_default("IMAGE_TAG", "devel")
image_ref := env_var_or_default("IMAGE_REF", "awx-devel:devel")
output := env_var_or_default("OUTPUT", "build/out/awx-devel.tar")

default:
    just --list

help:
    dagger functions

check:
    dagger call check --source=.

format:
    dagger call format --source=.

lint:
    dagger call lint --source=.

test:
    dagger call test --source=.

build:
    dagger call build --source=. \
      --upstream-ref="{{upstream_ref}}" \
      --awx-ui-repository="{{awx_ui_repo}}" \
      --awx-ui-ref="{{awx_ui_ref}}" \
      --image-name="{{image_name}}" \
      --image-tag="{{image_tag}}"

verify:
    dagger call verify --source=. \
      --upstream-ref="{{upstream_ref}}" \
      --awx-ui-repository="{{awx_ui_repo}}" \
      --awx-ui-ref="{{awx_ui_ref}}" \
      --image-name="{{image_name}}" \
      --image-tag="{{image_tag}}" \
      export --path=build/evidence

export:
    dagger call export --source=. \
      --upstream-ref="{{upstream_ref}}" \
      --awx-ui-repository="{{awx_ui_repo}}" \
      --awx-ui-ref="{{awx_ui_ref}}" \
      --image-ref="{{image_ref}}" \
      export --path="{{output}}"

clean:
    rm -rf build .pytest_cache .ruff_cache
    find . \( -path ./.git -o -path ./.venv -o -path ./build \) -prune -o -type d -name __pycache__ -exec rm -rf {} +

distclean: clean
    rm -rf .venv
