#!/bin/bash
# setup_dev.sh
# Corrected development environment setup script

set -e

echo "🚀 Setting up Solidus Development Environment"
echo "=============================================="

# Check project structure first
echo "📁 Checking project structure..."
if [ ! -f "manage.py" ]; then
    echo "❌ manage.py not found in root directory. Are you in the right folder?"
    exit 1
fi

if [ ! -d "src" ]; then
    echo "❌ src/ directory not found. Are you in the right folder?"
    exit 1
fi

if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found. Are you in the right folder?"
    exit 1
fi

echo "✅ Project structure looks correct"

# Check if .env exists and create it properly for HOST-based development
if [ ! -f .env ]; then
    echo "📝 Creating .env file for host-based development..."
    cat > .env << 'EOF'
# Solidus Environment Configuration - Host-based Development
DEBUG=True
SECRET_KEY=your-secret-key-here-change-in-production
DJANGO_SETTINGS_MODULE=solidus.settings
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database Configuration - HOST ADDRESSES (localhost for host-based migrations)
DB_NAME=solidus
DB_USER=solidus
DB_PASSWORD=solidus_password
DB_HOST=localhost
DB_PORT=5432

# Redis Configuration - HOST ADDRESS
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Email Configuration (Development)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=localhost
EMAIL_PORT=1025
EMAIL_USE_TLS=False
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@solidus.local

# Development Options
CREATE_SUPERUSER=True
LOAD_INITIAL_DATA=True
EOF
    echo "✅ .env file created for host-based development."
else
    echo "✅ .env file already exists."
    # Check if it has the right DB_HOST setting
    if grep -q "DB_HOST=postgres" .env; then
        echo "⚠️  Updating DB_HOST from 'postgres' to 'localhost' for host-based migrations..."
        sed -i 's/DB_HOST=postgres/DB_HOST=localhost/' .env
        sed -i 's/REDIS_HOST=redis/REDIS_HOST=localhost/' .env
        sed -i 's/EMAIL_HOST=mailhog/EMAIL_HOST=localhost/' .env
    fi
fi

# Check UV installation
if ! command -v uv &> /dev/null; then
    echo "❌ UV not found. Please install UV first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check Docker installation and new syntax
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

echo "🔍 Testing Docker Compose syntax..."
if docker compose version &> /dev/null; then
    echo "✅ Docker Compose v2 (new syntax) detected"
    DOCKER_COMPOSE="docker compose"
elif docker-compose version &> /dev/null; then
    echo "⚠️  Docker Compose v1 (old syntax) detected. Consider upgrading to Docker Compose v2"
    DOCKER_COMPOSE="docker-compose"
else
    echo "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
uv sync

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs media/uploads media/processed media/thumbnails static staticfiles
mkdir -p src/core/management/commands

# Stop any existing containers first
echo "🛑 Stopping any existing containers..."
$DOCKER_COMPOSE down || true

# Start PostgreSQL and Redis (expose ports to host)
echo "🗄️  Starting database services with exposed ports..."
$DOCKER_COMPOSE up -d postgres redis mailhog

# Wait for services to be ready with better error handling
echo "⏳ Waiting for services to be ready..."
echo "Checking PostgreSQL connection to localhost:5432..."

# Wait up to 60 seconds for PostgreSQL
POSTGRES_READY=false
for i in {1..60}; do
    if nc -z localhost 5432 2>/dev/null; then
        POSTGRES_READY=true
        break
    fi
    echo "  Attempt $i/60: PostgreSQL not ready yet..."
    sleep 1
done

if [ "$POSTGRES_READY" = false ]; then
    echo "❌ PostgreSQL not accessible on localhost:5432 after 60 seconds"
    echo "🔍 Checking docker compose logs..."
    $DOCKER_COMPOSE logs postgres
    echo ""
    echo "🔍 Checking if PostgreSQL container is running..."
    $DOCKER_COMPOSE ps postgres
    exit 1
fi

echo "Checking Redis connection to localhost:6379..."
REDIS_READY=false
for i in {1..30}; do
    if nc -z localhost 6379 2>/dev/null; then
        REDIS_READY=true
        break
    fi
    echo "  Attempt $i/30: Redis not ready yet..."
    sleep 1
done

if [ "$REDIS_READY" = false ]; then
    echo "❌ Redis not accessible on localhost:6379 after 30 seconds"
    echo "🔍 Checking docker compose logs..."
    $DOCKER_COMPOSE logs redis
    exit 1
fi

echo "✅ Services are ready!"

# Set Python path for host-based commands (Django apps are in src/)
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Load environment variables for host commands
set -a  # automatically export all variables
source .env
set +a

echo "🔍 Environment check:"
echo "  DB_HOST: $DB_HOST"
echo "  DB_PORT: $DB_PORT"
echo "  REDIS_HOST: $REDIS_HOST"
echo "  PYTHONPATH: $PYTHONPATH"

# Check Django can connect to database (manage.py is in root)
echo "🔍 Testing database connection..."
uv run python manage.py check --database default || {
    echo "❌ Django database check failed"
    echo "🔍 Checking Django configuration..."
    uv run python -c "
import os
import sys
sys.path.insert(0, 'src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'solidus.settings')
import django
django.setup()
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
    print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"
}

# Reset and create migrations in correct order
if [ "$1" = "--reset-migrations" ]; then
    echo "🔄 Resetting migrations..."
    uv run python manage.py reset_migrations --force
fi

# Create migrations for each app in dependency order
echo "📝 Creating migrations..."
APPS=("accounts" "core" "products" "assets" "feeds" "audit")

for app in "${APPS[@]}"; do
    echo "Creating migrations for $app..."
    uv run python manage.py makemigrations $app --verbosity=2
done

# Run migrations
echo "🔄 Running migrations..."
uv run python manage.py migrate --verbosity=2

# Create cache table
echo "🗄️  Creating cache table..."
uv run python manage.py createcachetable

# Load initial data
echo "📊 Loading initial data..."
if [ -f fixtures/initial_data.json ]; then
    uv run python manage.py loaddata fixtures/initial_data.json
else
    echo "⚠️  No initial data fixtures found"
fi

# Create superuser
echo "👤 Creating superuser..."
uv run python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@solidus.local',
        password='admin123',
        role='admin'
    )
    print('✅ Superuser created: admin / admin123')
else:
    print('ℹ️ Superuser already exists')
"

# Start all services
echo "🚀 Starting all services..."
$DOCKER_COMPOSE up -d

# Wait a moment for all services to start
echo "⏳ Waiting for all services to start..."
sleep 10

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "📊 Service Status:"
$DOCKER_COMPOSE ps
echo ""
echo "🌐 Access your application:"
echo "   • Main app: http://localhost:8000"
echo "   • Admin: http://localhost:8000/admin"
echo "   • Mailhog: http://localhost:8025"
echo ""
echo "🔑 Default login:"
echo "   • Username: admin"
echo "   • Password: admin123"
echo ""
echo "🛠️  Common commands:"
echo "   • make logs        - View logs"
echo "   • make shell       - Django shell"
echo "   • make migrate     - Run migrations (from host)"
echo "   • make test        - Run tests"
echo ""
echo "⚠️  If you encounter migration issues, run:"
echo "   ./setup-dev.sh --reset-migrations"
echo ""
echo "🔍 For debugging:"
echo "   • make status      - Check service status"
echo "   • make health      - Run health checks"
echo "   • make logs-web    - Web container logs"