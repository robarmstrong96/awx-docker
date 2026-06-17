.PHONY: doctor preflight build push print-tags

doctor:
	@./scripts/image.sh doctor

preflight:
	@./scripts/image.sh preflight

build:
	@./scripts/image.sh build

push:
	@./scripts/image.sh push

print-tags:
	@./scripts/image.sh print-tags
