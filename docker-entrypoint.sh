#!/bin/bash
# docker-entrypoint.sh

set -e

export PYTHONPATH="/app/src"

echo "Starting Solidus..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done
echo "PostgreSQL is ready!"

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! nc -z $REDIS_HOST 6379; do
  sleep 0.1
done
echo "Redis is ready!"

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Create cache table
echo "Creating cache table..."
python manage.py createcachetable || true

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create default superuser in development
if [ "$DEBUG" = "True" ] && [ "$CREATE_SUPERUSER" = "True" ]; then
    echo "Creating default superuser..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@solidus.local',
        password='admin123',
        role='admin'
    )
    print('Superuser created: admin / admin123')
else:
    print('Superuser already exists')
"
fi

# Load initial data if specified
if [ "$LOAD_INITIAL_DATA" = "True" ]; then
    echo "Loading initial data..."
    python manage.py loaddata initial_data || true
fi

# Create media directories
echo "Creating media directories..."
mkdir -p media/uploads media/processed media/thumbnails

# Set proper permissions
echo "Setting permissions..."
chown -R solidus:solidus media/ staticfiles/ logs/ || true

# Start the application
echo "Starting application..."
exec "$@"