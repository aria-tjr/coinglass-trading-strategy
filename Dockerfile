# Multi-stage build for telegram_coinglass_trader
# Production-ready Docker image with security and performance optimizations

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG POETRY_VERSION=1.7.1

# Set environment variables for build
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==$POETRY_VERSION

# Create and set working directory
WORKDIR /app

# Copy Poetry configuration
COPY pyproject.toml poetry.lock* ./

# Configure Poetry and install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-interaction --no-ansi

# Production stage
FROM python:3.11-slim as production

# Set production environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    TZ=UTC

# Create non-root user for security
RUN groupadd -r trader && useradd -r -g trader trader

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create application directories
WORKDIR /app
RUN mkdir -p /app/logs /app/data /app/backups \
    && chown -R trader:trader /app

# Copy application code
COPY --chown=trader:trader src/ ./src/
COPY --chown=trader:trader pyproject.toml ./

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Wait for dependencies if needed\n\
if [ -n "$WAIT_FOR_SERVICES" ]; then\n\
    echo "Waiting for services to be ready..."\n\
    sleep 10\n\
fi\n\
\n\
# Run database migrations if needed\n\
if [ "$RUN_MIGRATIONS" = "true" ]; then\n\
    echo "Running database migrations..."\n\
    # Add migration commands here when implemented\n\
fi\n\
\n\
# Start the trading bot\n\
echo "Starting telegram_coinglass_trader..."\n\
exec python -m src.main "$@"\n\
' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh \
    && chown trader:trader /app/entrypoint.sh

# Switch to non-root user
USER trader

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import asyncio; import sys; sys.path.insert(0, '/app/src'); \
    from infra.exchange_gateway import bybit_gateway; \
    result = asyncio.run(bybit_gateway.health_check()); \
    exit(0 if result else 1)" || exit 1

# Expose ports (if needed for monitoring)
EXPOSE 8080

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command
CMD []

# Labels for metadata
LABEL maintainer="CoinGlass Trader Team" \
      version="0.1.0" \
      description="Async Crypto Trading Bot with CoinGlass integration" \
      org.opencontainers.image.title="telegram_coinglass_trader" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.description="Production-grade async crypto trading bot" 