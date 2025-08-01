FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV PYTHONPATH="/app/src"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    imagemagick \
    libimage-exiftool-perl \
    curl \
    git \
  && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install uv (and make it globally available)
RUN curl -Ls https://astral.sh/uv/install.sh | bash && \
    ln -s "$HOME/.local/bin/uv" /usr/local/bin/uv

# Copy only lockfile and metadata first to optimize layer caching
COPY pyproject.toml uv.lock /app/

# Sync dependencies via UV
# Install only the dependencies from uv.lock (not dev and not the project itself)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# Now copy the rest of the project source into the container
COPY . /app

# Install the local project code itself into the environment
# This makes `solidus` importable by Django
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --editable .

# Create necessary directories
RUN mkdir -p /app/logs /app/media /app/staticfiles

# Copy and set permissions for entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Install netcat for health checks
RUN apt-get update && apt-get install -y netcat-openbsd \
  && rm -rf /var/lib/apt/lists/*

# Create non-root user
ARG UID=1000
ARG GID=1000

RUN groupadd -g $GID solidus && \
    useradd -u $UID -g solidus -m solidus && \
    chown -R solidus:solidus /app

# Switch to non-root user
USER solidus

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]

# Default command (can be overridden)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "solidus.asgi:application"]
