.DEFAULT_GOAL := help

COMPOSE ?= docker compose
SECRETS_ENV ?= secrets.env
ENV ?= development
COMPOSE_FILE ?= compose.yml
COMPOSE_SECRETS ?=
export NEXUS_ENV = $(ENV)
export NEXUS_CONFIG_DIR
export SECRETS_ENV
CONFIG = bash scripts/config.sh
# /dev/null disables Compose's implicit .env lookup: the helper loads literal values.
CONFIG_OVERLAY = $(if $(filter $(CURDIR)/compose.yml,$(abspath $(COMPOSE_FILE))),-f "compose.config.yml")
DC = $(CONFIG) run -- $(COMPOSE) --env-file /dev/null -f "$(COMPOSE_FILE)" $(CONFIG_OVERLAY) $(if $(COMPOSE_SECRETS),-f "$(COMPOSE_SECRETS)")

.PHONY: help \
        up down restart build rebuild ps logs \
        collect-secrets config-init config-path config-check config-test config-compose-test compose-check compose-ready \
        gateway gateway-up gateway-test gateway-config gateway-reload \
        auth website status overseer loadbalancer \
        auth-dbshell website-dbshell \
        blueprint-plan assemble deployment-validate assembler-test \
        clean prune

BLUEPRINT ?= composition/examples/nexus-development.yaml
DEPLOYMENT_PACKAGE ?= generated/nexus-development

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
	@echo " make config-init      Create private config.env and secret.env (no overwrite)"
	@echo " make config-path      Show runtime file locations (ENV=development|production)"
	@echo " make config-check     Check runtime file syntax and permissions"
	@echo " make compose-check    Validate the resolved Compose model without printing secrets"
	@echo " make config-test      Test the Bash configuration workflow"
	@echo " make config-compose-test  Test Compose mappings and secret isolation"
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
	@echo " make overseer         Start Overseer"
	@echo ""
	@echo "Product assembly"
	@echo "================"
	@echo " make blueprint-plan        Resolve the product blueprint"
	@echo " make assemble              Assemble the deployment package"
	@echo " make deployment-validate   Validate the deployment package"
	@echo " make assembler-test        Run Assembler and CLI tests"
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

config-init:
	@$(CONFIG) init

config-path:
	@$(CONFIG) path

config-check:
	@$(CONFIG) check

config-test:
	@bash scripts/tests/config_test.sh

# The root model is development-only; ENV selects files, not deployment policy.
compose-ready:
	@if [ "$(ENV)" = production ] && [ "$(abspath $(COMPOSE_FILE))" = "$(CURDIR)/compose.yml" ]; then \
	  echo "Select a production deployment with COMPOSE_FILE=...; root compose.yml is development-only." >&2; exit 1; \
	fi

up down build rebuild ps logs gateway-up gateway-test gateway-config gateway-reload auth website status overseer auth-dbshell website-dbshell clean compose-check: compose-ready

config-compose-test:
	@ruby scripts/tests/compose_config_test.rb

compose-check:
	@$(DC) config --quiet

collect-secrets:
	bin/nexus secrets --blueprint $(BLUEPRINT) --output secrets.env

##########################################
# Gateway lifecycle
##########################################

up:
	$(DC) up -d $(if $(filter development,$(ENV)),--build)

down:
	$(DC) down

restart:
	@$(MAKE) down
	@$(MAKE) up

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
	$(DC) up -d $(if $(filter development,$(ENV)),--build) gateway

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
	$(DC) up -d $(if $(filter development,$(ENV)),--build) keycloak keycloak-db

website: gateway-up
	$(DC) up -d website website-db

status: gateway-up
	$(DC) up -d status status-redis

overseer: gateway-up
	$(DC) up -d overseer

##########################################
# Product assembly
##########################################

blueprint-plan:
	bin/nexus plan --blueprint $(BLUEPRINT)

assemble:
	bin/nexus assemble --blueprint $(BLUEPRINT) --output $(DEPLOYMENT_PACKAGE) --force

deployment-validate:
	bin/nexus validate $(DEPLOYMENT_PACKAGE)

assembler-test:
	ruby tools/nexus_assembler/test/assembler_test.rb
	ruby tools/nexus_assembler/test/cli_test.rb
	ruby tools/nexus_assembler/test/repository_manager_test.rb

##########################################
# Database
##########################################

auth-dbshell:
	$(DC) exec keycloak-db sh -c 'exec psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

website-dbshell:
	$(DC) exec website-db sh -c 'export MYSQL_PWD="$${MYSQL_PASSWORD:-$$(cat "$${MYSQL_PASSWORD_FILE:-/dev/null}")}"; exec mysql -u "$$MYSQL_USER" "$$MYSQL_DATABASE"'

##########################################
# Cleanup
##########################################

clean:
	$(DC) down --remove-orphans

prune:
	docker system prune -af --volumes
