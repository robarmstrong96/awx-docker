.PHONY: doctor preflight resolve-ref write-metadata build verify-image push print-tags

doctor:
	@./scripts/image.sh doctor

preflight:
	@./scripts/image.sh preflight

resolve-ref:
	@./scripts/image.sh resolve-ref

write-metadata:
	@./scripts/image.sh write-metadata

build:
	@./scripts/image.sh build

verify-image:
	@./scripts/image.sh verify-image

push:
	@./scripts/image.sh push

print-tags:
	@./scripts/image.sh print-tags
