SHELL := /bin/sh

.DEFAULT_GOAL := help

PYTHON ?= python3
IMAGE ?= service-template:local
CONTAINER ?= service-template-smoke
PORT ?= 8000

.PHONY: help run test check build smoke clean

help: ## Show supported development commands.
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

run: ## Run the service locally.
	SERVICE_PORT=$(PORT) $(PYTHON) -m project

test: ## Run the unit tests.
	$(PYTHON) -m unittest discover -s tests -v

check: ## Run the complete local validation gate.
	$(PYTHON) -m compileall -q project tests
	$(PYTHON) -m unittest discover -s tests -v

build: ## Build the local container image.
	docker build -t $(IMAGE) .

smoke: build ## Start the image and verify its health endpoint.
	@set -eu; \
	cleanup() { docker rm --force "$(CONTAINER)" >/dev/null 2>&1 || true; }; \
	trap cleanup EXIT INT TERM; \
	cleanup; \
	docker run --detach --name "$(CONTAINER)" --publish "127.0.0.1:$(PORT):8000" "$(IMAGE)" >/dev/null; \
	attempt=1; \
	while [ "$$attempt" -le 20 ]; do \
		if curl --fail --silent "http://127.0.0.1:$(PORT)/healthz" >/dev/null; then \
			printf '%s\n' 'Smoke test passed.'; \
			exit 0; \
		fi; \
		attempt=$$((attempt + 1)); \
		sleep 1; \
	done; \
	docker logs "$(CONTAINER)"; \
	exit 1

clean: ## Remove Python caches without deleting developer configuration.
	find project tests -type d -name __pycache__ -prune -exec rm -rf {} +
