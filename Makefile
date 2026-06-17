.PHONY: doctor preflight public-hygiene resolve-ref write-metadata write-runner-diagnostics build verify-image push print-tags

doctor:
	@./scripts/image.sh doctor

preflight:
	@./scripts/image.sh preflight

public-hygiene:
	@./scripts/check-public-hygiene.sh

resolve-ref:
	@./scripts/image.sh resolve-ref

write-metadata:
	@./scripts/image.sh write-metadata

write-runner-diagnostics:
	@./scripts/image.sh write-runner-diagnostics

build:
	@./scripts/image.sh build

verify-image:
	@./scripts/image.sh verify-image

push:
	@./scripts/image.sh push

print-tags:
	@./scripts/image.sh print-tags
