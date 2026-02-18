# PHOEBE Server Docker Image

FROM python:3.12-slim

WORKDIR /app

# Install build and runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gfortran \
    libgfortran5 \
    tini \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install phoebe separately (large, slow to build, good for caching)
RUN pip install --no-cache-dir phoebe>=2.4.0

# Copy and install the application
COPY pyproject.toml .
COPY phoebe_server/ ./phoebe_server/
RUN pip install --no-cache-dir .

# Create data directory for database
RUN mkdir -p /app/data

# Copy entrypoint script
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Expose port 80 (internal)
EXPOSE 80

# Entrypoint handles init-db automatically (tini reaps worker processes)
ENTRYPOINT ["/usr/bin/tini", "--", "/app/docker-entrypoint.sh"]

# Run the server on port 80
CMD ["phoebe-server", "run", "--host", "0.0.0.0", "--port", "80"]
