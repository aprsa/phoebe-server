#!/bin/bash
set -e

# Initialize database if it doesn't exist
if [ ! -f /app/data/sessions.db ]; then
    echo "Initializing database..."
    phoebe-server init-db
fi

# Warn if JWT secret is empty in jwt/external mode
if grep -q 'mode = "jwt"\|mode = "external"' /app/config.toml 2>/dev/null; then
    if grep -q 'jwt_secret_key = ""' /app/config.toml 2>/dev/null; then
        echo ""
        echo "=========================================="
        echo "WARNING: jwt_secret_key is empty!"
        echo "Set a strong secret via environment variable:"
        echo "  export PHOEBE_JWT_SECRET_KEY=\"$(python -c 'import secrets; print(secrets.token_urlsafe(32))')\""
        echo "Then set jwt_secret_key in config.toml"
        echo "=========================================="
        echo ""
    fi
fi

# Run the main command
exec "$@"
