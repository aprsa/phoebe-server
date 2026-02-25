# PHOEBE Server

Backend server for PHOEBE computation and session management.

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)

## Features

- 🚀 **FastAPI** - Modern, fast REST API
- 🔄 **Session Management** - Multi-user session handling with idle timeouts
- ⚡ **ZMQ Workers** - Efficient PHOEBE process management
- 🔐 **Pluggable Auth** - JWT and internal authentication support
- 📊 **Resource Monitoring** - Memory and port tracking
- 💾 **SQLite Logging** - Session lifecycle and command history tracking
- 🐳 **Docker Ready** - Container deployment support

## Installation

```bash
# Basic installation
pip install .

# With development tools
pip install -e .[dev]

# With all optional dependencies
pip install -e .[all]
```

## Quick Start

### Initialize the database

```bash
phoebe-server init-db
```

or, if the database has been initialized before:

```bash
phoebe-server init-db --force
```

### Run the Server

```bash
phoebe-server run --port 8001
```

### Configuration

Create a `config.toml`:

```toml
[server]
host = "0.0.0.0"
port = 8001

[auth]
# Auth mode: "none" | "password" | "jwt" | "external"
mode = "jwt"
jwt_secret_key = ""  # Set via env var in production (see below)
jwt_algorithm = "HS256"
jwt_expire_minutes = 1440  # 24h

[port_pool]
start = 6560
end = 6590

[logging]
level = "INFO"
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

[session]
idle_timeout_seconds = 1800  # 30 minutes

[database]
path = "data/sessions.db"
log_exclude_commands = "ping"
log_include_commands = ""

[resources]
max_workers_per_user = 0  # 0 = unlimited
```

**JWT Secret**: In production, generate a strong secret and set it via environment variable:

```bash
> export PHOEBE_JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

The server refuses to start in `jwt`/`external` mode with an empty or `"test"` secret.

## Client Usage

Use with the PHOEBE client:

```python
from phoebe_client import PhoebeClient

client = PhoebeClient(base_url="http://localhost:8001")
with client:
    client.set_value(twig='period@binary', value=1.5)
    result = client.run_compute()
```

## API Documentation

Once running, visit:

- Swagger UI: <http://localhost:8001/docs>
- ReDoc: <http://localhost:8001/redoc>

## Database Logging

All session activity is logged to SQLite for tracking and analysis:

- **Session lifecycle**: Creation, destruction, idle timeouts
- **Command history**: Execution time, success/failure, errors
- **Memory metrics**: Resource usage over time
- **User tracking**: Client IP, user agent, user info
- **Configurable filtering**: Exclude low-value commands (e.g., ping)

Query the database directly:

```bash
sqlite3 data/sessions.db "SELECT * FROM sessions WHERE status='active'"
```

## Architecture

```text
Client Request → FastAPI (threadpool) → ZMQ Proxy → PHOEBE Worker
                     ↓                       ↓             ↓
                 Auth Layer            Session Mgr   PHOEBE Instance
                                          ↓
                                     SQLite DB
                                     (Logging)
```

### Components

- **FastAPI**: REST API with automatic OpenAPI docs. All endpoints are sync (`def`) and run in a threadpool for concurrent request handling.
- **Session Manager**: Lifecycle management, port allocation, idle cleanup. Uses in-memory state (single uvicorn worker required).
- **ZMQ Workers**: Isolated PHOEBE processes (one per session). Each worker handles SIGTERM for graceful shutdown and uses `LINGER=0` for clean socket release.
- **ZMQ Proxy**: Stateless REQ/REP client with configurable timeouts (default 5 min receive, 5s send). Context and socket are always cleaned up in `finally` blocks.
- **SQLite Database**: Session tracking and command logging (WAL mode).
- **PHOEBE Instance**: Binary star modeling engine.

### Concurrency

The server runs a **single uvicorn worker** (1 process). Session state is kept in module-level globals, so multiple workers would cause port collisions and invisible sessions. Concurrency comes from FastAPI's threadpool: each incoming request runs in its own thread, allowing multiple ZMQ calls to different PHOEBE workers simultaneously. All heavy computation happens in the worker subprocesses, not in the API process.
