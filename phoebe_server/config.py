"""Configuration management."""


from pathlib import Path
import tomli
from pydantic import BaseModel


class AuthConfig(BaseModel):
    # defaults when config.toml is missing
    enabled: bool = False


class ServerConfig(BaseModel):
    # defaults when config.toml is missing
    host: str = "0.0.0.0"
    port: int = 8001
    workers: int = 4


class PortPoolConfig(BaseModel):
    # defaults when config.toml is missing
    start: int = 6560
    end: int = 6590


class LoggingConfig(BaseModel):
    # defaults when config.toml is missing
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class SessionConfig(BaseModel):
    # defaults when config.toml is missing
    idle_timeout_seconds: int = 1800


class DatabaseConfig(BaseModel):
    # defaults when config.toml is missing
    path: str = "data/sessions.db"
    log_exclude_commands: str = "ping"
    log_include_commands: str = ""


class Config(BaseModel):
    server: ServerConfig = ServerConfig()
    auth: AuthConfig = AuthConfig()
    port_pool: PortPoolConfig = PortPoolConfig()
    logging: LoggingConfig = LoggingConfig()
    session: SessionConfig = SessionConfig()
    database: DatabaseConfig = DatabaseConfig()


def load_config(config_path: str = "config.toml") -> Config:
    """Load configuration from TOML file."""
    config_file = Path(config_path)

    if not config_file.exists():
        return Config()
    with open(config_file, "rb") as f:
        data = tomli.load(f)
    # Flatten nested dicts for pydantic
    return Config(**data)


# Global config instance
config = load_config()
