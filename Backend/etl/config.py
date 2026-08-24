"""Environment-driven configuration for the ETL pipelines.

Every path the pipelines need comes from here, resolved from environment
variables with sensible local fallbacks. Nothing in `etl/` may hardcode an
absolute path -- that is what kept the older loose scripts runnable only on
one machine.

Recognized variables:

    DATABASE_URL          Postgres connection string (falls back to Backend/.env)
    PSQL_PATH             psql executable (falls back to a default install, then PATH)
    LOCKLEY_ROMS_DIR      root holding retail ROM files for ROM-extraction pipelines
    LOCKLEY_DECOMPS_DIR   root holding pokered/pokecrystal/... decomp checkouts
    LOCKLEY_ETL_SOURCE_DIR root holding other source documents (e.g. ROM hack docs)
    LOCKLEY_PREVIEW_DIR   where preview CSVs are written (default: Backend/)
"""
import os
import re
import shutil
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PSQL = r"C:\Program Files\PostgreSQL\18\bin\psql.exe"


class ConfigError(RuntimeError):
    """Raised when required configuration is missing."""


def database_url():
    """Postgres URL from the environment, falling back to Backend/.env."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    env_path = BACKEND_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = re.match(r"\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
            if match:
                return match.group(1).strip().strip("\"'")
    raise ConfigError("DATABASE_URL is not set in the environment or Backend/.env")


def psql_path():
    """Path to the psql executable."""
    configured = os.environ.get("PSQL_PATH")
    if configured:
        return configured
    if Path(DEFAULT_PSQL).exists():
        return DEFAULT_PSQL
    found = shutil.which("psql")
    if found:
        return found
    raise ConfigError("psql not found; set PSQL_PATH")


def _source_dir(env_var, description):
    value = os.environ.get(env_var)
    if not value:
        raise ConfigError(
            f"{env_var} is not set; point it at {description} to run this pipeline"
        )
    path = Path(value)
    if not path.exists():
        raise ConfigError(f"{env_var} points at a missing directory: {path}")
    return path


def roms_dir():
    return _source_dir("LOCKLEY_ROMS_DIR", "the directory holding retail ROM files")


def decomps_dir():
    return _source_dir("LOCKLEY_DECOMPS_DIR", "the directory holding decomp checkouts")


def source_dir():
    return _source_dir("LOCKLEY_ETL_SOURCE_DIR", "the directory holding ETL source documents")


def preview_dir(name):
    """Directory for a pipeline's preview CSVs.

    Defaults to Backend/<name> so existing preview folders keep working.
    """
    base = os.environ.get("LOCKLEY_PREVIEW_DIR")
    root = Path(base) if base else BACKEND_DIR
    return root / name
