set shell := ["bash", "-uc"]

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
    dagger call build --source=.

verify:
    dagger call verify --source=.

export:
    dagger call export --source=. export --path=build/out/awx-devel.tar

clean:
    rm -rf build .pytest_cache .ruff_cache
    find . \( -path ./.git -o -path ./.venv -o -path ./build \) -prune -o -type d -name __pycache__ -exec rm -rf {} +

distclean: clean
    rm -rf .venv
