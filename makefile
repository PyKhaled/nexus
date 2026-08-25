.DEFAULT_GOAL := help

COMPOSE ?= docker compose
SECRETS_ENV ?= secrets.env
SECRETS_ENV_FLAG = $(if $(wildcard $(SECRETS_ENV)),--env-file $(SECRETS_ENV))
DC = $(COMPOSE) $(SECRETS_ENV_FLAG) -f compose.yml

.PHONY: help \
        up down restart build rebuild ps logs \
        collect-secrets \
        gateway gateway-up gateway-test gateway-config gateway-reload \
        auth website status loadbalancer \
        auth-dbshell website-dbshell \
        clean prune

help:
	@echo ""
	@echo "Development environment"
	@echo "======================="
	@echo " make up               Build and start the complete environment"
	@echo " make down             Stop the complete environment"
	@echo " make restart          Restart the complete environment"
	@echo " make ps               Show development containers"
	@echo " make logs             Tail development logs"
	@echo " make build            Build local images"
	@echo " make rebuild          Build local images without cache"
	@echo " make collect-secrets  Merge service .env files into secrets.env"
	@echo ""
	@echo "Operations"
	@echo "=========="
	@echo " make gateway-test     Validate generated NGINX config"
	@echo " make gateway-config   Print generated NGINX config"
	@echo " make gateway-reload   Validate and reload NGINX"
	@echo ""
	@echo "Individual service groups"
	@echo "========================="
	@echo " make gateway          Start only the gateway"
	@echo " make auth             Start Keycloak + Postgres"
	@echo " make website          Start WordPress + MySQL"
	@echo " make status           Start Kener + Redis"
	@echo ""
	@echo "Database"
	@echo "========"
	@echo " make auth-dbshell     Open a Keycloak Postgres shell"
	@echo " make website-dbshell  Open a WordPress MySQL shell"
	@echo ""
	@echo "Cleanup"
	@echo "======="
	@echo " make clean            Stop and remove gateway orphans"
	@echo " make prune            Remove all Docker images/volumes (destructive)"

##########################################
# Secrets
##########################################

collect-secrets:
	./scripts/collect-secrets.sh

##########################################
# Gateway lifecycle
##########################################

up:
	$(DC) up -d --build

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

gateway: gateway-up

gateway-up:
	$(DC) up -d --build gateway

gateway-test:
	$(DC) run --rm --no-deps gateway nginx -t

gateway-config:
	$(DC) run --rm --no-deps gateway nginx -T

gateway-reload:
	$(DC) exec gateway nginx -t
	$(DC) exec gateway nginx -s reload

# Backward-compatible alias for the old component name.
loadbalancer: gateway-up

##########################################
# Optional backend stacks
##########################################

auth: gateway-up
	$(DC) up -d --build keycloak keycloak-db

website: gateway-up
	$(DC) up -d website website-db

status: gateway-up
	$(DC) up -d status status-redis

##########################################
# Database
##########################################

auth-dbshell:
	$(DC) exec keycloak-db psql -U $${KC_DB_USERNAME:-keycloak}

website-dbshell:
	$(DC) exec website-db mysql -u $${MYSQL_USER:-wordpress} -p$${MYSQL_PASSWORD:-change-me-wordpress-password} $${MYSQL_DATABASE:-wordpress}

##########################################
# Cleanup
##########################################

clean:
	$(DC) down --remove-orphans

prune:
	docker system prune -af --volumes
