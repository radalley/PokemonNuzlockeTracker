"""psql invocation helpers shared by every ETL pipeline.

The pipelines drive Postgres through psql rather than psycopg2 because they
rely on `\\copy` for bulk staging, which is a psql client feature.
"""
import subprocess
import tempfile
from pathlib import Path

from . import config


class PsqlError(RuntimeError):
    """psql exited non-zero.

    The message carries psql's own diagnostics; a loader that aborts on a
    guard is the normal way this surfaces, so the reason has to be readable
    rather than buried in a traceback.
    """

    def __init__(self, returncode, stdout, stderr):
        detail = (stderr or stdout or "").strip()
        message = f"psql failed with exit code {returncode}"
        if detail:
            message = f"{message}\n{detail}"
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _run(args, url=None):
    return subprocess.run(
        [
            config.psql_path(),
            url or config.database_url(),
            "-X",
            "-v",
            "ON_ERROR_STOP=1",
            "-P",
            "pager=off",
            *args,
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def run_sql(sql, url=None):
    """Execute a SQL script, returning psql's stdout.

    The script is written to a temp file so `\\copy` metacommands work.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        sql_file = Path(temp_dir) / "script.sql"
        sql_file.write_text(sql, encoding="utf-8")
        result = _run(["-f", str(sql_file)], url=url)
    if result.returncode:
        raise PsqlError(result.returncode, result.stdout, result.stderr)
    return result.stdout, result.stderr


def query_rows(sql, url=None):
    """Run a single query and return its rows as lists of column strings."""
    result = _run(["-A", "-t", "-F", "\t", "-c", sql], url=url)
    if result.returncode:
        raise PsqlError(result.returncode, result.stdout, result.stderr)
    return [line.split("\t") for line in result.stdout.splitlines() if line.strip()]


def query_scalar(sql, url=None):
    """Run a query expected to yield one value; returns None when empty."""
    rows = query_rows(sql, url=url)
    if not rows or not rows[0]:
        return None
    return rows[0][0]
