# Dockerfile
FROM python:3.12-slim

# Build arguments for user/group IDs
ARG UID=1000
ARG GID=1000

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    libmagic1 \
    imagemagick \
    exiftool \
    && rm -rf /var/lib/apt/lists/*

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create solidus user with specified UID/GID
RUN groupadd -g ${GID} solidus && \
    useradd -u ${UID} -g ${GID} -m -s /bin/bash solidus

# Set work directory
WORKDIR /app

# Copy UV configuration
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy project
COPY . .

# Set up directories and permissions
RUN mkdir -p /app/media /app/staticfiles /app/logs && \
    chown -R solidus:solidus /app

# Switch to solidus user
USER solidus

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Default command
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "solidus.asgi:application"]