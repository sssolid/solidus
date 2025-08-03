#!/bin/bash
# docker-entrypoint.sh

set -e

# Set Python path for Django
export PYTHONPATH="/app/src:$PYTHONPATH"

echo "🚀 Starting Solidus..."
echo "🐍 Python path: $PYTHONPATH"
echo "📍 Working directory: $(pwd)"

# Debug: Check if Django is available using uv run
echo "🔍 Checking Django installation..."
uv run python -c "import django; print(f'Django version: {django.get_version()}')" || {
    echo "❌ Django not found! Checking Python path..."
    uv run python -c "import sys; print('Python path:'); [print(p) for p in sys.path]"
    echo "📦 Checking installed packages..."
    uv pip list | grep -i django || echo "Django not in pip list"
    exit 1
}

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done
echo "✅ PostgreSQL is ready!"

# Wait for Redis to be ready
echo "⏳ Waiting for Redis..."
while ! nc -z $REDIS_HOST 6379; do
  sleep 0.1
done
echo "✅ Redis is ready!"

# Run migrations
echo "🔄 Running migrations..."
uv run python manage.py migrate --noinput

# Create cache table
echo "🗄️ Creating cache table..."
uv run python manage.py createcachetable || true

# Collect static files
echo "📁 Collecting static files..."
uv run python manage.py collectstatic --noinput

# Create default superuser in development
if [ "$DEBUG" = "True" ] && [ "$CREATE_SUPERUSER" = "True" ]; then
    echo "👤 Creating default superuser..."
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
fi

# Load initial data if specified
if [ "$LOAD_INITIAL_DATA" = "True" ]; then
    echo "📊 Loading initial data..."
    uv run python manage.py loaddata initial_data || true
fi

# Create media directories
echo "📁 Creating media directories..."
mkdir -p media/uploads media/processed media/thumbnails

# Set proper permissions
echo "🔒 Setting permissions..."
chown -R solidus:solidus media/ staticfiles/ logs/ || true

# Start the application
echo "🎉 Starting application..."
exec "$@"