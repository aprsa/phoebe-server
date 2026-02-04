#!/bin/bash
set -e

# Initialize database if it doesn't exist
if [ ! -f /app/data/sessions.db ]; then
    echo "Initializing database..."
    phoebe-server init-db
fi

# Generate API key if none configured
# Check if api_keys array is empty in config.toml
if grep -q 'api_keys = \[\]' /app/config.toml 2>/dev/null; then
    echo ""
    echo "=========================================="
    echo "WARNING: No API keys configured!"
    echo "Generate a key with:"
    echo "  docker exec phoebe-server phoebe-server generate-key"
    echo "Then add it to config.toml under [auth] api_keys"
    echo "=========================================="
    echo ""
fi

# Run the main command
exec "$@"
