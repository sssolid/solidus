# Makefile
# Development Makefile for Solidus Project with UV

# Variables
DOCKER_COMPOSE = docker-compose
# Use uv run to automatically activate the virtual environment
DJANGO_MANAGE = $(DOCKER_COMPOSE) exec web uv run python manage.py
DJANGO_SHELL = $(DOCKER_COMPOSE) exec web uv run python manage.py shell_plus

# Help command
.PHONY: help
help:
	@echo "🚀 Solidus Development Commands"
	@echo ""
	@echo "📦 Setup & Dependencies:"
	@echo "  make install          - Install dependencies with UV"
	@echo "  make install-dev      - Install dev dependencies"
	@echo "  make sync             - Sync dependencies with uv.lock"
	@echo "  make update           - Update dependencies"
	@echo ""
	@echo "🐳 Docker Commands:"
	@echo "  make build            - Build Docker images"
	@echo "  make rebuild          - Build images with no cache"
	@echo "  make up               - Start all services"
	@echo "  make down             - Stop all services"
	@echo "  make restart          - Restart all services"
	@echo "  make logs             - View logs"
	@echo "  make logs-web         - View web container logs"
	@echo "  make logs-worker      - View worker container logs"
	@echo ""
	@echo "🗄️  Database Commands:"
	@echo "  make migrate          - Run migrations"
	@echo "  make makemigrations   - Create migrations"
	@echo "  make dbshell          - Database shell"
	@echo "  make dbreset          - Reset database (⚠️  DESTRUCTIVE)"
	@echo "  make fixtures         - Load initial data"
	@echo ""
	@echo "👤 User Management:"
	@echo "  make superuser        - Create superuser"
	@echo "  make dev-data         - Create development data"
	@echo ""
	@echo "🧪 Testing & Quality:"
	@echo "  make test             - Run tests"
	@echo "  make test-coverage    - Run tests with coverage"
	@echo "  make lint             - Run linters"
	@echo "  make format           - Format code"
	@echo "  make type-check       - Run type checking"
	@echo ""
	@echo "🛠️  Development Tools:"
	@echo "  make shell            - Django shell"
	@echo "  make bash             - Bash shell in web container"
	@echo "  make collectstatic    - Collect static files"
	@echo "  make clean            - Clean up containers and volumes"
	@echo ""
	@echo "📊 Monitoring:"
	@echo "  make status           - Show service status"
	@echo "  make health           - Health check"
	@echo "  make pgadmin          - Start pgAdmin"

# UV-based dependency management (local)
.PHONY: install
install:
	@echo "📦 Installing dependencies with UV..."
	uv sync

.PHONY: install-dev
install-dev:
	@echo "📦 Installing dev dependencies..."
	uv sync --group dev

.PHONY: sync
sync:
	@echo "🔄 Syncing dependencies..."
	uv sync

.PHONY: update
update:
	@echo "⬆️  Updating dependencies..."
	uv lock --upgrade

.PHONY: add
add:
	@echo "➕ Adding dependency..."
	@read -p "Package name: " pkg; \
	uv add $$pkg

.PHONY: add-dev
add-dev:
	@echo "➕ Adding dev dependency..."
	@read -p "Package name: " pkg; \
	uv add --group dev $$pkg

# Docker commands
.PHONY: build
build:
	@echo "🏗️  Building Docker images for: $(filter-out $@,$(MAKECMDGOALS))"
	$(DOCKER_COMPOSE) build $(filter-out $@,$(MAKECMDGOALS))

.PHONY: rebuild
rebuild:
	@echo "🏗️  Rebuilding Docker images for: $(filter-out $@,$(MAKECMDGOALS))"
	$(DOCKER_COMPOSE) build --no-cache $(filter-out $@,$(MAKECMDGOALS))

.PHONY: up
up:
	@echo "🚀 Starting Solidus services..."
	$(DOCKER_COMPOSE) up -d
	@echo ""
	@echo "✅ Solidus is running!"
	@echo "🌐 Main app: http://localhost:8000"
	@echo "📧 Mailhog: http://localhost:8025"
	@echo "🗄️  pgAdmin: make pgadmin"

.PHONY: down
down:
	@echo "🛑 Stopping services..."
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

# Django commands (simplified - no need to specify venv path)
.PHONY: shell
shell:
	@echo "🐍 Starting Django shell..."
	$(DJANGO_SHELL)

.PHONY: bash
bash:
	@echo "💻 Starting bash shell..."
	$(DOCKER_COMPOSE) exec web bash

.PHONY: migrate
migrate:
	@echo "🔄 Running migrations..."
	$(DJANGO_MANAGE) migrate

.PHONY: makemigrations
makemigrations:
	@echo "📝 Creating migrations..."
	$(DJANGO_MANAGE) makemigrations

.PHONY: collectstatic
collectstatic:
	@echo "📁 Collecting static files..."
	$(DJANGO_MANAGE) collectstatic --noinput

# Database commands
.PHONY: dbshell
dbshell:
	@echo "🗄️  Starting database shell..."
	$(DOCKER_COMPOSE) exec postgres psql -U solidus solidus

.PHONY: dbreset
dbreset:
	@echo "⚠️  WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "🗑️  Resetting database..."; \
		$(DOCKER_COMPOSE) down -v; \
		$(DOCKER_COMPOSE) up -d postgres redis; \
		sleep 5; \
		$(DOCKER_COMPOSE) up -d; \
		sleep 5; \
		$(DJANGO_MANAGE) migrate; \
		$(DJANGO_MANAGE) loaddata fixtures/initial_data.json; \
		echo "✅ Database reset complete!"; \
	fi

.PHONY: pgadmin
pgadmin:
	@echo "🚀 Starting pgAdmin..."
	$(DOCKER_COMPOSE) --profile tools up -d pgadmin
	@echo "✅ pgAdmin is running at http://localhost:5050"
	@echo "📧 Email: admin@solidus.local"
	@echo "🔑 Password: admin"

# Development commands
.PHONY: fixtures
fixtures:
	@echo "📊 Loading initial data..."
	$(DJANGO_MANAGE) loaddata fixtures/initial_data.json

.PHONY: dev-data
dev-data:
	@echo "🎯 Creating development data..."
	$(DJANGO_MANAGE) create_dev_data --reset

.PHONY: superuser
superuser:
	@echo "👤 Creating superuser..."
	$(DJANGO_MANAGE) createsuperuser

# Testing and quality
.PHONY: test
test:
	@echo "🧪 Running tests..."
	uv run pytest
#	$(DOCKER_COMPOSE) exec web uv run pytest

.PHONY: test-coverage
test-coverage:
	@echo "📊 Running tests with coverage..."
	uv run pytest --cov=. --cov-report=html
#	$(DOCKER_COMPOSE) exec web uv run pytest --cov=. --cov-report=html
	@echo "📝 Coverage report: htmlcov/index.html"

.PHONY: lint
lint:
	@echo "🔍 Running linters..."
	uv run ruff check src/
	uv run black src/ --check
#	$(DOCKER_COMPOSE) exec web uv run ruff check src/
#	$(DOCKER_COMPOSE) exec web uv run black src/ --check

.PHONY: format
format:
	@echo "✨ Formatting code..."
	uv run black src/
	uv run ruff check src/ --fix
#	$(DOCKER_COMPOSE) exec web uv run black src/
#	$(DOCKER_COMPOSE) exec web uv run ruff check src/ --fix

.PHONY: type-check
type-check:
	@echo "🔍 Running type checks..."
	uv run mypy src/
#	$(DOCKER_COMPOSE) exec web uv run mypy src/

# Asset processing
.PHONY: process-assets
process-assets:
	@echo "🖼️  Processing assets..."
	$(DJANGO_MANAGE) process_assets

.PHONY: generate-thumbnails
generate-thumbnails:
	@echo "🖼️  Generating thumbnails..."
	$(DJANGO_MANAGE) generate_thumbnails

# Feed operations
.PHONY: generate-feeds
generate-feeds:
	@echo "📊 Generating feeds..."
	$(DJANGO_MANAGE) generate_scheduled_feeds

# Monitoring and maintenance
.PHONY: status
status:
	@echo "📊 Service Status:"
	$(DOCKER_COMPOSE) ps

.PHONY: health
health:
	@echo "🏥 Health check..."
	@curl -f http://localhost:8000/health/ 2>/dev/null && echo "✅ Service healthy" || echo "❌ Service not healthy"

.PHONY: backup
backup:
	@echo "💾 Creating database backup..."
	@mkdir -p backups
	$(DOCKER_COMPOSE) exec postgres pg_dump -U solidus solidus > backups/solidus_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup created in backups/ directory"

.PHONY: restore
restore:
	@echo "📥 Database restore..."
	@read -p "Enter backup file name: " backup_file; \
	$(DOCKER_COMPOSE) exec -T postgres psql -U solidus -d solidus < backups/$$backup_file

# Cleanup
.PHONY: clean
clean:
	@echo "🧹 Cleaning up..."
	$(DOCKER_COMPOSE) down -v
	docker system prune -f
	@echo "✅ Cleanup complete!"

.PHONY: clean-data
clean-data:
	@echo "⚠️  WARNING: This will delete all data volumes!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE) down -v; \
		echo "✅ Data volumes deleted!"; \
	fi

# This is the magic that prevents "No rule to make target 'web'" errors
%:
	@: