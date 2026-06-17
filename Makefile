.PHONY: doctor preflight resolve-ref build push print-tags

doctor:
	@./scripts/image.sh doctor

preflight:
	@./scripts/image.sh preflight

resolve-ref:
	@./scripts/image.sh resolve-ref

build:
	@./scripts/image.sh build

push:
	@./scripts/image.sh push

print-tags:
	@./scripts/image.sh print-tags
