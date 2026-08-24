"""Apply pending SQL migrations in filename order.

Every migration file in this directory must be self-guarded: wrapped in a
transaction, safe to re-run (IF NOT EXISTS / IF EXISTS guards for DDL), with
one-shot data backfills gated on a schema_migrations row the file inserts
itself. This runner therefore executes every file in order on every run;
"pending" work is whatever the guards let through. It reports which
schema_migrations rows each run added.

Usage:
    python migrations/apply.py            # applies against DATABASE_URL
    python migrations/apply.py --dry-run  # lists files and applied state only

DATABASE_URL is read from the environment first, then Backend/.env. Point it
at production (Supabase) to apply there; psql location comes from PSQL_PATH,
the default PostgreSQL 18 install path, or PATH.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = MIGRATIONS_DIR.parent
DEFAULT_PSQL = r"C:\Program Files\PostgreSQL\18\bin\psql.exe"


def database_url():
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    env_path = BACKEND_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = re.match(r"\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
            if match:
                return match.group(1).strip().strip("\"'")
    raise RuntimeError("DATABASE_URL not set in the environment or Backend/.env")


def psql_path():
    configured = os.environ.get("PSQL_PATH")
    if configured:
        return configured
    if Path(DEFAULT_PSQL).exists():
        return DEFAULT_PSQL
    found = shutil.which("psql")
    if found:
        return found
    raise RuntimeError("psql not found; set PSQL_PATH")


def run_psql(url, *args, check=True):
    result = subprocess.run(
        [psql_path(), url, "-X", "-v", "ON_ERROR_STOP=1", "-P", "pager=off", *args],
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result


def applied_migrations(url):
    result = run_psql(
        url, "-A", "-t", "-c",
        "select migration_name from schema_migrations order by migration_name;",
        check=False,
    )
    if result.returncode != 0:
        # schema_migrations may not exist yet; the first migration creates it.
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="List migration files and applied rows without executing anything.")
    args = parser.parse_args()

    url = database_url()
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        print("No migration files found.")
        return

    before = applied_migrations(url)
    print(f"schema_migrations rows before: {len(before)}")
    for name in sorted(before):
        print(f"  applied: {name}")

    if args.dry_run:
        for path in files:
            print(f"would run: {path.name}")
        return

    for path in files:
        print(f"running: {path.name}")
        result = run_psql(url, "-f", str(path), check=False)
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            print(f"FAILED: {path.name}", file=sys.stderr)
            sys.exit(1)
        if result.stderr.strip():
            # psql emits RAISE NOTICE lines (e.g. backfill counts) on stderr.
            print(result.stderr.strip())

    after = applied_migrations(url)
    new = sorted(after - before)
    if new:
        for name in new:
            print(f"newly applied: {name}")
    else:
        print("No new schema_migrations rows; all migrations were already applied.")


if __name__ == "__main__":
    main()
