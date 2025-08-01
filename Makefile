# Makefile

# Variables
DOCKER_COMPOSE = docker-compose
DJANGO_MANAGE = $(DOCKER_COMPOSE) exec web python manage.py
DJANGO_SHELL = $(DOCKER_COMPOSE) exec web python manage.py shell_plus

# Help command
.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make build          - Build Docker images"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - View logs"
	@echo "  make shell          - Django shell"
	@echo "  make bash           - Bash shell in web container"
	@echo "  make migrate        - Run migrations"
	@echo "  make makemigrations - Create migrations"
	@echo "  make superuser      - Create superuser"
	@echo "  make test           - Run tests"
	@echo "  make lint           - Run linters"
	@echo "  make clean          - Clean up containers and volumes"

# Docker commands
.PHONY: build
build:
	$(DOCKER_COMPOSE) build

.PHONY: up
up:
	$(DOCKER_COMPOSE) up -d
	@echo "Solidus is running at http://localhost"
	@echo "Mailhog is running at http://localhost:8025"
	@echo "pgAdmin is available with: make pgadmin"

.PHONY: down
down:
	$(DOCKER_COMPOSE) down

.PHONY: restart
restart: down up

.PHONY: logs
logs:
	$(DOCKER_COMPOSE) logs -f

.PHONY: logs-web
logs-web:
	$(DOCKER_COMPOSE) logs -f web

.PHONY: logs-worker
logs-worker:
	$(DOCKER_COMPOSE) logs -f worker

# Django commands
.PHONY: shell
shell:
	$(DJANGO_SHELL)

.PHONY: bash
bash:
	$(DOCKER_COMPOSE) exec web bash

.PHONY: migrate
migrate:
	$(DJANGO_MANAGE) migrate

.PHONY: makemigrations
makemigrations:
	$(DJANGO_MANAGE) makemigrations

.PHONY: superuser
superuser:
	$(DJANGO_MANAGE) createsuperuser

.PHONY: collectstatic
collectstatic:
	$(DJANGO_MANAGE) collectstatic --noinput

# Database commands
.PHONY: dbshell
dbshell:
	$(DOCKER_COMPOSE) exec postgres psql -U solidus solidus

.PHONY: dbreset
dbreset:
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE) down -v; \
		$(DOCKER_COMPOSE) up -d postgres; \
		sleep 5; \
		$(DOCKER_COMPOSE) up -d; \
		sleep 5; \
		$(DJANGO_MANAGE) migrate; \
		$(DJANGO_MANAGE) loaddata initial_data; \
	fi

# Development commands
.PHONY: fixtures
fixtures:
	$(DJANGO_MANAGE) loaddata initial_data

.PHONY: test
test:
	$(DOCKER_COMPOSE) exec web pytest

.PHONY: test-coverage
test-coverage:
	$(DOCKER_COMPOSE) exec web pytest --cov=. --cov-report=html

.PHONY: lint
lint:
	$(DOCKER_COMPOSE) exec web black . --check
	$(DOCKER_COMPOSE) exec web isort . --check-only
	$(DOCKER_COMPOSE) exec web flake8

.PHONY: format
format:
	$(DOCKER_COMPOSE) exec web black .
	$(DOCKER_COMPOSE) exec web isort .

# Asset processing
.PHONY: process-assets
process-assets:
	$(DJANGO_MANAGE) process_assets

.PHONY: generate-feeds
generate-feeds:
	$(DJANGO_MANAGE) generate_feeds

# Optional services
.PHONY: pgadmin
pgadmin:
	$(DOCKER_COMPOSE) --profile tools up -d pgadmin
	@echo "pgAdmin is running at http://localhost:5050"
	@echo "Login: admin@solidus.local / admin"

# Cleanup
.PHONY: clean
clean:
	$(DOCKER_COMPOSE) down -v --remove-orphans
	docker system prune -f

.PHONY: clean-all
clean-all: clean
	docker system prune -a -f --volumes

# Production-like commands
.PHONY: prod-build
prod-build:
	docker build -f Dockerfile.prod -t solidus:latest .

.PHONY: prod-run
prod-run:
	docker run -d \
		--name solidus_prod \
		-p 8000:8000 \
		--env-file .env.prod \
		solidus:latest