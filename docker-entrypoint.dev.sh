#!/bin/bash
# docker-entrypoint.dev.sh
# Development-optimized entrypoint script

set -e

echo "🚀 Starting Solidus Development Server..."
echo "========================================="

# Set Python path for Django apps in src/
export PYTHONPATH="/app/src:$PYTHONPATH"

echo "🔍 Environment check:"
echo "  PYTHONPATH: $PYTHONPATH"
echo "  DEBUG: $DEBUG"
echo "  DB_HOST: $DB_HOST"

# Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done
echo "✅ PostgreSQL is ready!"

# Wait for Redis
echo "⏳ Waiting for Redis..."
while ! nc -z $REDIS_HOST 6379; do
  sleep 0.1
done
echo "✅ Redis is ready!"

# Install any new dependencies (in case pyproject.toml changed)
echo "📦 Checking for dependency updates..."
uv sync --dev

# Create cache table (safe to run multiple times)
echo "🗄️ Creating cache table..."
uv run python manage.py createcachetable || true

# Create media directories
echo "📁 Creating media directories..."
mkdir -p media/uploads media/processed media/thumbnails

# Set proper permissions for media
echo "🔒 Setting permissions..."
chmod -R 755 media/ || true

# Only run migrations if this is the main web container (not worker)
if [ "${CONTAINER_ROLE:-web}" = "web" ]; then
    echo "🔄 Checking for pending migrations..."
    if uv run python manage.py showmigrations --plan | grep -q '\[ \]'; then
        echo "📝 Running pending migrations..."
        uv run python manage.py migrate --verbosity=1
    else
        echo "✅ No pending migrations"
    fi

    # Create superuser in development
    if [ "$DEBUG" = "True" ] && [ "$CREATE_SUPERUSER" = "True" ]; then
        echo "👤 Checking for default superuser..."
        uv run python manage.py shell -c "
try:
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
except Exception as e:
    print(f'⚠️ Could not create superuser: {e}')
"
    fi

    # Collect static files for development
    echo "📁 Collecting static files..."
    uv run python manage.py collectstatic --noinput --verbosity=0 || true
fi

echo ""
echo "🎉 Development environment ready!"
echo ""
echo "📋 Development Features Enabled:"
echo "  • Hot reloading for Python files"
echo "  • Template auto-reload"
echo "  • Static file serving"
echo "  • Debug toolbar (if installed)"
echo "  • Detailed error pages"
echo ""
echo "🌐 Access your application:"
echo "  • Main app: http://localhost:8000"
echo "  • Admin: http://localhost:8000/admin (admin/admin123)"
echo ""

# Start the application
echo "🚀 Starting development server with auto-reload..."
exec "$@"