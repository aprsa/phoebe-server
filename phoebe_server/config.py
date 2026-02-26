"""Configuration management.

Deployment modes and their paths:

1. Editable install (pip install -e):
    - Config: <project_root>/config.toml

2. venv install (pip install):
    - Config: ~/.config/phoebe-server/config.toml

3. System-wide install (sudo pip install) and Docker:
    - Config: /etc/phoebe-server/config.toml

Uses built-in defaults if config file is missing.
"""

from dataclasses import dataclass, field
from pathlib import Path
import os
import sys
import tomllib


def _find_project_root() -> Path | None:
    """Walk up from this file looking for pyproject.toml (editable install)."""
    current = Path(__file__).parent.resolve()
    while True:
        if (current / "pyproject.toml").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _in_virtualenv() -> bool:
    """Return True when running inside a virtual environment."""
    base_prefix = getattr(sys, "base_prefix", sys.prefix)
    return sys.prefix != base_prefix


_PROJECT_ROOT = _find_project_root()

if _PROJECT_ROOT is not None:
    CONFIG_PATH = _PROJECT_ROOT / "config.toml"
elif _in_virtualenv():
    CONFIG_PATH = Path.home() / ".config" / "phoebe-server" / "config.toml"
else:
    CONFIG_PATH = Path("/etc/phoebe-server/config.toml")


@dataclass(frozen=True)
class AuthConfig:
    mode: str = "none"  # none | password | jwt | external
    password: str = ""  # gate password for mode=password
    jwt_secret_key: str = ""  # signing/verification key for jwt & external
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24h, jwt mode only
    jwt_issuer: str = ""  # expected iss claim; blank = skip validation


@dataclass(frozen=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8001
    workers: int = 4


@dataclass(frozen=True)
class PortPoolConfig:
    start: int = 6560
    end: int = 6590


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass(frozen=True)
class SessionConfig:
    idle_timeout_seconds: int = 1800


@dataclass(frozen=True)
class DatabaseConfig:
    path: str = "data/sessions.db"
    log_exclude_commands: str = "ping"
    log_include_commands: str = ""


@dataclass(frozen=True)
class ResourceConfig:
    max_workers_per_user: int = 0  # 0 = unlimited


@dataclass(frozen=True)
class Config:
    server: ServerConfig = field(default_factory=ServerConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    port_pool: PortPoolConfig = field(default_factory=PortPoolConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    resources: ResourceConfig = field(default_factory=ResourceConfig)


def _resolve_db_path(raw_path: str) -> str:
    """Resolve database path relative to project root if not absolute."""
    p = Path(raw_path)
    if p.is_absolute():
        return raw_path
    if _PROJECT_ROOT is not None:
        return str(_PROJECT_ROOT / p)
    return raw_path


def load_config() -> Config:
    """Load configuration from TOML file."""
    if not CONFIG_PATH.is_file():
        return Config()

    try:
        with CONFIG_PATH.open("rb") as f:
            data = tomllib.load(f)
    except Exception:
        return Config()

    def get_args(config_cls, section_data):
        return {
            k: v for k, v in section_data.items()
            if v is not None and k in config_cls.__dataclass_fields__
        }

    db_data = data.get("database", {})
    if "path" in db_data:
        db_data = {**db_data, "path": _resolve_db_path(db_data["path"])}

    auth_data = data.get("auth", {})
    # Allow overriding jwt_secret_key via environment variable
    env_secret = os.environ.get("PHOEBE_JWT_SECRET_KEY")
    if env_secret:
        auth_data = {**auth_data, "jwt_secret_key": env_secret}

    return Config(
        server=ServerConfig(**get_args(ServerConfig, data.get("server", {}))),
        auth=AuthConfig(**get_args(AuthConfig, auth_data)),
        port_pool=PortPoolConfig(**get_args(PortPoolConfig, data.get("port_pool", {}))),
        logging=LoggingConfig(**get_args(LoggingConfig, data.get("logging", {}))),
        session=SessionConfig(**get_args(SessionConfig, data.get("session", {}))),
        database=DatabaseConfig(**get_args(DatabaseConfig, db_data)),
        resources=ResourceConfig(**get_args(ResourceConfig, data.get("resources", {}))),
    )


# Global config instance
config = load_config()
