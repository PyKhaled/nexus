.DEFAULT_GOAL := help

COMPOSE = docker compose
DC = $(COMPOSE) -f docker-compose.yml

.PHONY: help \
        up down restart build rebuild ps logs \
        auth website loadbalancer \
        auth-dbshell website-dbshell \
        clean prune

help:
	@echo ""
	@echo "Stack"
	@echo "====="
	@echo " make up               Start all services"
	@echo " make down             Stop everything"
	@echo " make restart          Restart stack"
	@echo " make ps               Running containers"
	@echo " make logs             Tail all logs"
	@echo " make build            Build images"
	@echo " make rebuild          Build without cache"
	@echo ""
	@echo "Services"
	@echo "========"
	@echo " make auth             Start auth-server + auth-worker"
	@echo " make website          Start website + website-db"
	@echo " make loadbalancer     Start loadbalancer"
	@echo ""
	@echo "Database"
	@echo "========"
	@echo " make auth-dbshell     psql into auth-db"
	@echo " make website-dbshell  mysql into website-db"
	@echo ""
	@echo "Cleanup"
	@echo "======="
	@echo " make clean            Stop and remove orphans"
	@echo " make prune            Remove all containers, images, volumes"

##########################################
# Stack
##########################################

up:
	$(DC) up -d

down:
	$(DC) down

restart: down up

build:
	$(DC) build

rebuild:
	$(DC) build --no-cache

ps:
	$(DC) ps

logs:
	$(DC) logs -f

##########################################
# Services
##########################################

auth:
	$(DC) up auth-server auth-worker

website:
	$(DC) up website website-db

loadbalancer:
	$(DC) up loadbalancer

##########################################
# Database
##########################################

auth-dbshell:
	$(DC) exec auth-db psql -U $${PG_USER:-authentik}

website-dbshell:
	$(DC) exec website-db mysql -u $${MYSQL_USER:-wordpress} -p$${MYSQL_PASSWORD} $${MYSQL_DATABASE:-wordpress}

##########################################
# Cleanup
##########################################

clean:
	$(DC) down --remove-orphans

prune:
	docker system prune -af --volumes
