# Solidus Docker Development Setup

This guide will help you get Solidus running locally using Docker.

## Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose)
- Make (optional, but recommended)
- 4GB+ RAM allocated to Docker

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd solidus
   ```

2. **Copy environment variables**
   ```bash
   cp .env.example .env
   ```

3. **Build and start services**
   ```bash
   make build
   make up
   ```

   Or without make:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

4. **Create a superuser**
   ```bash
   make superuser
   ```

5. **Access the application**
   - Main application: http://localhost
   - Admin interface: http://localhost/admin
   - Mailhog (email testing): http://localhost:8025
   - pgAdmin (optional): http://localhost:5050

## Services

### Core Services

- **web**: Django application (port 8000)
- **postgres**: PostgreSQL database (port 5432)
- **redis**: Redis cache and message broker (port 6379)
- **nginx**: Reverse proxy and static file server (port 80)
- **worker**: Background task processor

### Development Tools

- **mailhog**: Email testing interface (ports 1025, 8025)
- **pgadmin**: PostgreSQL administration tool (port 5050) - use `make pgadmin` to start

## Common Commands

### Docker Management
```bash
make up          # Start all services
make down        # Stop all services
make restart     # Restart all services
make logs        # View logs for all services
make logs-web    # View logs for web service only
make clean       # Remove containers and volumes
```

### Django Commands
```bash
make shell       # Django shell
make bash        # Bash shell in web container
make migrate     # Run migrations
make makemigrations  # Create new migrations
make test        # Run tests
make lint        # Run code linters
make format      # Format code with black/isort
```

### Database Commands
```bash
make dbshell     # PostgreSQL shell
make dbreset     # Reset database (WARNING: deletes all data)
```

### Asset Processing
```bash
make process-assets   # Process pending assets
make generate-feeds   # Generate scheduled feeds
```

## Development Workflow

1. **Making code changes**
   - Code changes are automatically reflected (hot reload)
   - No need to restart containers for Python code changes

2. **Adding dependencies**
   - Add to `requirements.txt`
   - Rebuild: `make build`
   - Restart: `make restart`

3. **Database changes**
   ```bash
   make makemigrations
   make migrate
   ```

4. **Running tests**
   ```bash
   make test
   make test-coverage  # With coverage report
   ```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs web

# Rebuild from scratch
make clean
make build
make up
```

### Database connection errors
```bash
# Ensure PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres
```

### Permission errors
```bash
# Fix ownership issues
docker-compose exec web chown -R solidus:solidus /app/media /app/staticfiles
```

### Port conflicts
If you get port binding errors, either:
1. Stop conflicting services
2. Or modify ports in `docker-compose.yml`

## Environment Variables

Key environment variables (see `.env.example` for full list):

- `DEBUG`: Enable debug mode (default: True)
- `SECRET_KEY`: Django secret key
- `DB_*`: Database connection settings
- `REDIS_HOST`: Redis hostname
- `EMAIL_*`: Email configuration (uses Mailhog in dev)

## Data Persistence

The following directories are persisted in Docker volumes:
- PostgreSQL data
- Redis data  
- Media files
- Static files

To completely reset:
```bash
make clean  # This will delete all data!
```

## Production Considerations

This setup is for **development only**. For production:

1. Use proper secrets management
2. Enable SSL/TLS
3. Use a production WSGI server (Gunicorn)
4. Configure proper logging
5. Set up monitoring (Sentry, etc.)
6. Use managed services for PostgreSQL and Redis
7. Configure S3 or similar for media storage

## Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)