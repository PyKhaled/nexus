SHELL := /bin/bash

# Make is verbose in Linux. Make it silent.
MAKEFLAGS += --silent

# Include .env file if it exists
-include .env
export

# Delete the default suffixes
.SUFFIXES:

BASE_DIR := ${CURDIR}

# Git remote server
GIT_REMOTE_URL := $(shell git remote get-url origin)
GIT_REMOTE_BRANCH = main

# Default goal is to show help
.DEFAULT_GOAL := help
.PHONY: help version quickstart configuration lint format build test launch clean show info









quickstart: ## Quickstart everything
	@echo "Setting the default environment variables..."
	@sleep 3
	@echo "Creating virtual environment..."
	@sleep 3
	@echo "Activating the newly created virtual environment..."
	@sleep 3
	@echo "Upgrading pip..."
	@sleep 3
	@echo "Installing requirements..."
	@sleep 3
	@echo "Running database migrations..."
	@sleep 3
	@echo "Loading fixtures files..."
	@sleep 3

configuration: ## Setup configuration
	@echo "Setting up configuration..."

lint: ## Lint the code
	@echo "Linting code..."

format: ## Format the code
	@echo "Formatting code..."

build: ## Build the project
	@echo "Building project..."

test: ## Run tests
	@echo "Running tests..."

launch: ## Launch the application
	@echo "Launching application..."

deploy: ## Deploy your code into development environment
	# access ssh server
	@echo "Connecting to development server via ssh..."
	$(info ssh remote_username@remote_host)
	$(info ssh -i ${SERVER_KEY_FILE} -N ${username}@${host})
	@sleep 3
	
	# Install required system dependencies
	@echo "Installing required system dependencies"
	$(info apt-get update)
	$(info apt-get install --no-install-recommends -y build-essential libpq-dev libcairo2-dev gettext git)
	@sleep 3

	# cleaning up unused files
	$(info apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false)
	@sleep 3

	# clone repository
	@echo "Cloning the repository"
	$(info git clone ${REPO_URL} ${APPLICATION_PATH}/${APPLICATION_NAME})
	@sleep 3

	# pull the code from git remote server
	@echo "Pulling code from git remote server"
	$(info git pull origin {feature_branch} {development_branch})
	@sleep 3

	# Install required application dependencies
	@echo "Installing required application dependencies"
	$(info pip install -r requirements.txt)
	@sleep 3

	# run check command
	$(info python manage.py check)
	@sleep 3

	# run collecstatic command
	$(info python manage.py collectstatic --noinput)
	@sleep 3
	
	# run migration command
	$(info python manage.py migrate)
	@sleep 3

	# run server command
	$(info python manage.py runserver ${APPLICATION_HOST}:${APPLCIATION_PORT} --noreload --nothreading)
	$(info python manage.py runserver 0.0.0.0:8000)
	$(info gunicorn ${PROJECT}.wsgi:application --bind 0.0.0.0:8000 --workers 3 --log-level=info --reload)
	@sleep 3



clean: ## Remove all output files
	@echo "Cleaning up..."

show: ## Show variables (for debug use only)
	@echo 'BASE_DIR: $(BASE_DIR)'
	@echo 'PROJECT: $(PROJECT)'
	@echo 'CONFIG: $(CONFIG)'
	@echo 'SCHEME: $(SCHEME)'
	@echo 'ICON_TAG: $(ICON_TAG)'
	@echo 'GIT_REMOTE_URL: $(GIT_REMOTE_URL)'
	@echo 'GIT_REMOTE_BRANCH: $(GIT_REMOTE_BRANCH)'
	@echo 'SERVER_HOST: $(SERVER_HOST)'
	@echo 'SERVER_PORT: $(SERVER_PORT)'
	@echo 'SERVER_USER: $(SERVER_USER)'
	@echo 'SERVER_PASS: $(SERVER_PASS)'
	@echo 'SERVER_KEY_FILE: $(SERVER_KEY_FILE)'

help: ## Show this help
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*##";} /^[$$()% a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

version: ## Print the current version
	@echo "${APPLICATION_NAME} 1.0.0"

info: ## Show project info
	@echo "GIT_REMOTE_URL: $(GIT_REMOTE_URL)"
	@echo "GIT_REMOTE_BRANCH: $(GIT_REMOTE_BRANCH)"
	
	@echo "SERVER_HOST: $(SERVER_HOST)"
	@echo "SERVER_PORT: $(SERVER_PORT)"
	@echo "SERVER_USER: $(SERVER_USER)"
	@echo "SERVER_PASS: $(SERVER_PASS)"
	@echo "SERVER_KEY_FILE: $(SERVER_KEY_FILE)"
	

# Route all unknown targets to framework command utility
%: $(lastword $(MAKEFILE_LIST))
	@python3 -m pip $@

# Empty target to avoid errors for undefined commands
@:
	@echo "Command not recognized."
