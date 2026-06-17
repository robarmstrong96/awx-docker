.PHONY: doctor bootstrap update render dockerfile build up up-build down logs ps admin-password compose clean-containers clean-volumes

doctor:
	@./scripts/awx-compose.sh doctor

bootstrap:
	@./scripts/awx-compose.sh bootstrap

update:
	@./scripts/awx-compose.sh update

render:
	@./scripts/awx-compose.sh render

dockerfile:
	@./scripts/awx-compose.sh dockerfile

build:
	@./scripts/awx-compose.sh build

up:
	@./scripts/awx-compose.sh up

up-build:
	@./scripts/awx-compose.sh up-build

down:
	@./scripts/awx-compose.sh down

logs:
	@./scripts/awx-compose.sh logs

ps:
	@./scripts/awx-compose.sh ps

admin-password:
	@./scripts/awx-compose.sh admin-password

compose:
	@./scripts/awx-compose.sh compose $(ARGS)

clean-containers:
	@./scripts/awx-compose.sh clean-containers

clean-volumes:
	@./scripts/awx-compose.sh clean-volumes
