# PHOEBE Server Docker Image

FROM python:3.12-slim

WORKDIR /app

# Install build and runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gfortran \
    libgfortran5 \
    git \
    tini \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Optional PHOEBE source override at build time. Defaults to PyPI install unless both args are provided.
# This is driven from docker-compose.yaml to allow testing of branches and PRs without needing to publish to PyPI.
ARG PHOEBE_GIT_REMOTE=""
ARG PHOEBE_GIT_BRANCH=""

# Install phoebe separately (large, slow to build, good for caching).
# Examples:
#   --build-arg PHOEBE_GIT_REMOTE=https://github.com/aprsa/phoebe2 \
#   --build-arg PHOEBE_GIT_BRANCH=dc-sb1-fix
RUN if [ -n "$PHOEBE_GIT_REMOTE" ] && [ -n "$PHOEBE_GIT_BRANCH" ]; then \
            pip install --no-cache-dir "git+$PHOEBE_GIT_REMOTE@$PHOEBE_GIT_BRANCH"; \
        else \
            pip install --no-cache-dir "phoebe>=2.4.0"; \
        fi

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
