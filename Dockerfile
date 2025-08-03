FROM python:3.12-slim

ARG UID=1000
ARG GID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    libmagic1 \
    imagemagick \
    exiftool \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

RUN groupadd -g ${GID} solidus && \
    useradd -u ${UID} -g ${GID} -m -s /bin/bash solidus

WORKDIR /app

COPY pyproject.toml uv.lock ./

COPY . .

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN uv venv $VIRTUAL_ENV && uv sync --frozen

RUN mkdir -p /app/media /app/staticfiles /app/logs && \
    chown -R solidus:solidus /app

RUN chmod +x /app/docker-entrypoint.sh

USER solidus

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "solidus.asgi:application"]