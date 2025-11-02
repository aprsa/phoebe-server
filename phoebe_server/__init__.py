"""PHOEBE Server - Computation and session management backend."""

try:
    from importlib.metadata import version
    __version__ = version("phoebe-server")
except Exception:
    __version__ = "unknown"
