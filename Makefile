# Makefile
# Corrected Makefile for Solidus Project

# Variables
DOCKER_COMPOSE = docker compose
DOCKER_COMPOSE_PROD = docker compose -f docker-compose.yml -f docker-compose.prod.yml

# Use UV for local Django commands (manage.py is in root, not src/)
LOCAL_DJANGO = uv run python manage.py
CONTAINER_DJANGO = $(DOCKER_COMPOSE) exec web uv run python manage.py

# Local Python path setup (Django apps are in src/)
export PYTHONPATH := $(PWD)/src:$(PYTHONPATH)

# Load environment for host-based commands
-include .env
export

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
	@echo "  make up-db            - Start only database services"
	@echo "  make down             - Stop all services"
	@echo "  make restart          - Restart all services"
	@echo "  make logs             - View logs"
	@echo "  make logs-web         - View web container logs"
	@echo "  make logs-worker      - View worker container logs"
	@echo ""
	@echo "🗄️  Database & Migration Commands (HOST-BASED):"
	@echo "  make migrate          - Run migrations (on host → localhost:5432)"
	@echo "  make makemigrations   - Create migrations (on host)"
	@echo "  make reset-migrations - Reset and recreate migrations"
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

# Docker commands (using new syntax)
.PHONY: build
build:
	@echo "🏗️  Building Docker images..."
	$(DOCKER_COMPOSE) build $(filter-out $@,$(MAKECMDGOALS))

.PHONY: rebuild
rebuild:
	@echo "🏗️  Rebuilding Docker images..."
	$(DOCKER_COMPOSE) build --no-cache $(filter-out $@,$(MAKECMDGOALS))

.PHONY: up-db
up-db:
	@echo "🗄️  Starting database services only..."
	$(DOCKER_COMPOSE) up -d postgres redis mailhog

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

# HOST-BASED Django commands (manage.py is in root folder)
.PHONY: shell
shell:
	@echo "🐍 Starting Django shell (local with localhost DB)..."
	@echo "📍 DB_HOST: $(DB_HOST) | DB_PORT: $(DB_PORT)"
	$(LOCAL_DJANGO) shell_plus

.PHONY: bash
bash:
	@echo "💻 Starting bash shell..."
	$(DOCKER_COMPOSE) exec web bash

# CRITICAL: Run migrations on HOST using localhost:5432 (manage.py in root)
.PHONY: migrate
migrate:
	@echo "🔄 Running migrations (host → localhost:5432)..."
	@echo "📍 Ensuring database is accessible at $(DB_HOST):$(DB_PORT)..."
	@until nc -z $(DB_HOST) $(DB_PORT); do echo "⏳ Waiting for database..."; sleep 1; done
	@echo "✅ Database accessible!"
	$(LOCAL_DJANGO) migrate --verbosity=2

.PHONY: makemigrations
makemigrations:
	@echo "📝 Creating migrations (host → localhost:5432)..."
	@echo "📍 Using DB: $(DB_HOST):$(DB_PORT)"
	$(LOCAL_DJANGO) makemigrations --verbosity=2

.PHONY: reset-migrations
reset-migrations:
	@echo "🔄 Resetting migrations..."
	@echo "📍 Using DB: $(DB_HOST):$(DB_PORT)"
	$(LOCAL_DJANGO) reset_migrations

.PHONY: collectstatic
collectstatic:
	@echo "📁 Collecting static files..."
	$(LOCAL_DJANGO) collectstatic --noinput

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
		$(DOCKER_COMPOSE) up -d postgres redis mailhog; \
		sleep 10; \
		make reset-migrations; \
		make migrate; \
		make fixtures; \
		$(DOCKER_COMPOSE) up -d; \
		echo "✅ Database reset complete!"; \
	fi

.PHONY: fixtures
fixtures:
	@echo "📊 Loading initial data..."
	$(LOCAL_DJANGO) loaddata fixtures/initial_data.json || echo "⚠️  No fixtures found"

# User management
.PHONY: superuser
superuser:
	@echo "👤 Creating superuser..."
	$(LOCAL_DJANGO) createsuperuser

.PHONY: dev-data
dev-data:
	@echo "📊 Creating development data..."
	$(LOCAL_DJANGO) create_dev_data

# Testing and quality (from root directory)
.PHONY: test
test:
	@echo "🧪 Running tests..."
	uv run pytest

.PHONY: test-coverage
test-coverage:
	@echo "🧪 Running tests with coverage..."
	uv run pytest --cov=src --cov-report=html --cov-report=term

.PHONY: lint
lint:
	@echo "🔍 Running linters..."
	uv run ruff check src/
	uv run black --check src/
	uv run isort --check-only src/

.PHONY: format
format:
	@echo "✨ Formatting code..."
	uv run black src/
	uv run isort src/
	uv run ruff check --fix src/

.PHONY: type-check
type-check:
	@echo "🔍 Running type check..."
	uv run mypy src/

# Monitoring and maintenance
.PHONY: status
status:
	@echo "📊 Service Status:"
	$(DOCKER_COMPOSE) ps
	@echo ""
	@echo "🔍 Connection Check:"
	@nc -z localhost 5432 && echo "✅ PostgreSQL (localhost:5432)" || echo "❌ PostgreSQL (localhost:5432)"
	@nc -z localhost 6379 && echo "✅ Redis (localhost:6379)" || echo "❌ Redis (localhost:6379)"
	@nc -z localhost 8000 && echo "✅ Web Server (localhost:8000)" || echo "❌ Web Server (localhost:8000)"

.PHONY: health
health:
	@echo "🏥 Health Check:"
	@curl -f http://localhost:8000/health/ 2>/dev/null && echo "✅ Web service healthy" || echo "❌ Web service unhealthy"
	@$(DOCKER_COMPOSE) exec postgres pg_isready -U solidus > /dev/null 2>&1 && echo "✅ PostgreSQL healthy" || echo "❌ PostgreSQL unhealthy"
	@$(DOCKER_COMPOSE) exec redis redis-cli ping > /dev/null 2>&1 && echo "✅ Redis healthy" || echo "❌ Redis unhealthy"

.PHONY: pgadmin
pgadmin:
	@echo "🗄️  Starting pgAdmin..."
	$(DOCKER_COMPOSE) --profile tools up -d pgadmin
	@echo "🌐 pgAdmin: http://localhost:5050"
	@echo "📧 Email: admin@solidus.local"
	@echo "🔑 Password: admin"

# Cleanup
.PHONY: clean
clean:
	@echo "🧹 Cleaning up..."
	$(DOCKER_COMPOSE) down -v --remove-orphans
	docker image prune -f
	docker volume prune -f

# Background processing
.PHONY: process-assets
process-assets:
	@echo "📷 Processing assets..."
	$(LOCAL_DJANGO) process_assets

.PHONY: generate-feeds
generate-feeds:
	@echo "📊 Generating feeds..."
	$(LOCAL_DJANGO) generate_feeds

# Production commands
.PHONY: prod-build
prod-build:
	@echo "🏗️  Building production images..."
	$(DOCKER_COMPOSE_PROD) build

.PHONY: prod-up
prod-up:
	@echo "🚀 Starting production services..."
	$(DOCKER_COMPOSE_PROD) up -d

.PHONY: prod-down
prod-down:
	@echo "🛑 Stopping production services..."
	$(DOCKER_COMPOSE_PROD) down

# Environment check
.PHONY: env-check
env-check:
	@echo "🔍 Environment Configuration Check:"
	@echo "  DB_HOST: $(DB_HOST)"
	@echo "  DB_PORT: $(DB_PORT)"
	@echo "  REDIS_HOST: $(REDIS_HOST)"
	@echo "  REDIS_PORT: $(REDIS_PORT)"
	@echo ""
	@echo "🌐 Expected for host-based development:"
	@echo "  DB_HOST should be 'localhost' (not 'postgres')"
	@echo "  REDIS_HOST should be 'localhost' (not 'redis')"

# Project structure check
.PHONY: check-structure
check-structure:
	@echo "📁 Project Structure Check:"
	@echo "  manage.py exists in root: $$([ -f manage.py ] && echo '✅' || echo '❌')"
	@echo "  src/ directory exists: $$([ -d src ] && echo '✅' || echo '❌')"
	@echo "  docker-compose.yml exists: $$([ -f docker-compose.yml ] && echo '✅' || echo '❌')"
	@echo "  .env exists: $$([ -f .env ] && echo '✅' || echo '❌')"

# Enhanced development commands
.PHONY: dev
dev:
	@echo "🚀 Starting DEVELOPMENT environment with hot reloading..."
	@echo ""
	@echo "📋 Features enabled:"
	@echo "  • Python hot reloading (edit .py files)"
	@echo "  • Template hot reloading (edit .html files)"
	@echo "  • Static file serving (edit .css/.js files)"
	@echo "  • Database on localhost:5432"
	@echo "  • Redis on localhost:6379"
	@echo ""
	docker compose -f docker-compose.dev.yml up -d
	@echo ""
	@echo "✅ Development environment started!"
	@echo "🌐 Main app: http://localhost:8000"
	@echo "📧 Mailhog: http://localhost:8025"
	@echo ""
	@echo "🔄 File changes will automatically reload the server"
	@echo "📝 View logs: make dev-logs"

.PHONY: dev-build
dev-build:
	@echo "🏗️ Building development containers..."
	docker compose -f docker-compose.dev.yml build

.PHONY: dev-frontend
dev-frontend:
	@echo "🏗️ Building frontend js/css..."
	cd frontend && npm run build
	cp frontend/node_modules/@fortawesome/fontawesome-free/webfonts/* static/webfonts/

.PHONY: dev-logs
dev-logs:
	@echo "📋 Development server logs (Ctrl+C to exit):"
	docker compose -f docker-compose.dev.yml logs -f web

.PHONY: dev-logs-all
dev-logs-all:
	@echo "📋 All development logs (Ctrl+C to exit):"
	docker compose -f docker-compose.dev.yml logs -f

.PHONY: dev-shell
dev-shell:
	@echo "🐍 Starting Django shell in development container..."
	docker compose -f docker-compose.dev.yml exec web uv run python manage.py shell_plus

.PHONY: dev-bash
dev-bash:
	@echo "💻 Starting bash shell in development container..."
	docker compose -f docker-compose.dev.yml exec web bash

.PHONY: dev-down
dev-down:
	@echo "🛑 Stopping development environment..."
	docker compose -f docker-compose.dev.yml down

.PHONY: dev-restart
dev-restart:
	@echo "🔄 Restarting development environment..."
	docker compose -f docker-compose.dev.yml restart web
	@echo "✅ Development server restarted!"

.PHONY: dev-reset
dev-reset:
	@echo "🔄 Resetting development environment..."
	docker compose -f docker-compose.dev.yml down -v
	docker compose -f docker-compose.dev.yml build
	$(MAKE) dev
	@echo "✅ Development environment reset!"

.PHONY: dev-clean-reset
dev-clean-reset:
	@echo "🗑️  Performing a full development clean reset..."
	docker compose -f docker-compose.dev.yml down -v
	docker compose -f docker-compose.dev.yml build
	$(LOCAL_DJANGO) makemigrations
	${MAKE} dev-frontend
	$(LOCAL_DJANGO) reset_migrations
	$(MAKE) dev
	@echo "✅ Full development environment clean and rebuild complete!"

# File watching and hot reload status
.PHONY: dev-status
dev-status:
	@echo "📊 Development Environment Status:"
	@echo "=================================="
	docker compose -f docker-compose.dev.yml ps
	@echo ""
	@echo "🔄 Hot Reload Features:"
	@echo "  • Python files (.py): ✅ Auto-reload on save"
	@echo "  • Templates (.html): ✅ Auto-reload on save"
	@echo "  • Static files (.css/.js): ✅ Served directly"
	@echo "  • Settings changes: ⚠️ Restart required"
	@echo "  • New dependencies: ⚠️ Rebuild required"
	@echo ""
	@echo "🌐 Access Points:"
	@curl -s http://localhost:8000/health/ > /dev/null && echo "  • App: ✅ http://localhost:8000" || echo "  • App: ❌ http://localhost:8000"
	@curl -s http://localhost:8025/ > /dev/null && echo "  • Mailhog: ✅ http://localhost:8025" || echo "  • Mailhog: ❌ http://localhost:8025"

# Development testing
.PHONY: dev-test
dev-test:
	@echo "🧪 Running tests in development environment..."
	docker compose -f docker-compose.dev.yml exec web uv run pytest -v

.PHONY: dev-test-watch
dev-test-watch:
	@echo "🧪 Running tests with file watching..."
	docker compose -f docker-compose.dev.yml exec web uv run pytest-watch

# Hot reload verification
.PHONY: test-hotreload
test-hotreload:
	@echo "🔥 Testing hot reload functionality..."
	@echo ""
	@echo "1. Make sure development server is running: make dev"
	@echo "2. Edit a Python file (e.g., add a comment to a view)"
	@echo "3. Check logs: make dev-logs"
	@echo "4. You should see: 'Performing system checks...'"
	@echo "5. Edit a template file"
	@echo "6. Refresh browser - changes should appear immediately"
	@echo ""
	@echo "📁 Files that trigger auto-reload:"
	@echo "  • Python files: src/**/*.py"
	@echo "  • Templates: templates/**/*.html"
	@echo "  • Settings: src/solidus/settings.py"
	@echo ""
	@echo "📁 Files served directly (no restart needed):"
	@echo "  • Static files: static/**/*"
	@echo "  • Media files: media/**/*"

# Productivity helpers
.PHONY: dev-migrate
dev-migrate:
	@echo "🔄 Running migrations in development..."
	docker compose -f docker-compose.dev.yml exec web uv run python manage.py migrate

.PHONY: dev-makemigrations
dev-makemigrations:
	@echo "📝 Creating migrations in development..."
	docker compose -f docker-compose.dev.yml exec web uv run python manage.py makemigrations

.PHONY: dev-superuser
dev-superuser:
	@echo "👤 Creating superuser in development..."
	docker compose -f docker-compose.dev.yml exec web uv run python manage.py createsuperuser

.PHONY: dev-collectstatic
dev-collectstatic:
	@echo "📁 Collecting static files in development..."
	docker compose -f docker-compose.dev.yml exec web uv run python manage.py collectstatic --noinput

# Performance monitoring for development
.PHONY: dev-profile
dev-profile:
	@echo "📊 Development performance monitoring..."
	@echo "  • Container stats: docker stats solidus_web"
	@echo "  • Memory usage: docker compose -f docker-compose.dev.yml exec web free -h"
	@echo "  • Disk usage: docker compose -f docker-compose.dev.yml exec web df -h"
	@echo ""
	@echo "🔍 Django debug toolbar should be available if installed"

# Help for development workflow
.PHONY: dev-help
dev-help:
	@echo "🛠️ Solidus Development Workflow"
	@echo "==============================="
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make dev              - Start development environment"
	@echo "  make dev-logs         - View server logs"
	@echo "  make dev-status       - Check status"
	@echo ""
	@echo "📝 Making Changes:"
	@echo "  Edit Python files    - Auto-reload (see logs)"
	@echo "  Edit templates        - Auto-reload (refresh browser)"
	@echo "  Edit static files     - Refresh browser"
	@echo "  Edit settings         - Run: make dev-restart"
	@echo "  Add dependencies      - Run: make dev-build && make dev"
	@echo ""
	@echo "🗄️ Database:"
	@echo "  make dev-migrate      - Run migrations"
	@echo "  make dev-makemigrations - Create migrations"
	@echo "  make dev-shell        - Django shell"
	@echo ""
	@echo " Frontend"
	@echo "  make dev-frontend     - Frontend (js/css)"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make dev-test         - Run tests"
	@echo "  make test-hotreload   - Verify hot reload"
	@echo ""
	@echo "🔧 Troubleshooting:"
	@echo "  make dev-restart      - Restart web server"
	@echo "  make dev-reset        - Full reset"
	@echo "  make dev-clean-reset  - Full clean reset"
	@echo "  make dev-logs         - View detailed logs"

# Allow passing additional arguments to specific commands
%:
	@: