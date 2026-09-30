"""Guarded staged-load framework.

Every loader in this repo follows the same shape, previously copy-pasted per
generation:

    BEGIN
      create TEMP stage tables
      \\copy the preview CSVs into them
      DO $$ ... RAISE EXCEPTION ... $$   -- refuse to load anything unexpected
      INSERT ... SELECT from stage
      report metrics
    COMMIT (only with --apply) / ROLLBACK

`GuardedLoad` owns that shape so a pipeline only declares its stage tables,
its guards, its insert statements, and the metrics worth printing.

The default is always a dry run: nothing commits without `--apply`.
"""
import argparse
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import db, preview


@dataclass
class StageTable:
    """A TEMP table the preview rows are copied into before validation."""

    name: str
    columns: list  # list[(column_name, sql_type)]
    rows: list
    fields: list = None  # CSV column order; defaults to the declared columns

    def csv_fields(self):
        return self.fields or [name for name, _ in self.columns]

    def ddl(self):
        cols = ",\n  ".join(f"{name} {sql_type}" for name, sql_type in self.columns)
        return f"CREATE TEMP TABLE {self.name} (\n  {cols}\n) ON COMMIT DROP;"


@dataclass
class Guard:
    """A condition that must NOT hold; the load aborts when it does."""

    fail_when: str  # SQL boolean expression
    message: str


@dataclass
class Metric:
    """A scalar query reported after the load."""

    name: str
    sql: str


@dataclass
class GuardedLoad:
    title: str
    stages: list
    guards: list = field(default_factory=list)
    statements: list = field(default_factory=list)
    metrics: list = field(default_factory=list)

    def build_sql(self, staged_paths, rollback):
        parts = ["BEGIN;", ""]
        for stage in self.stages:
            parts.append(stage.ddl())
        parts.append("")
        for stage in self.stages:
            path = Path(staged_paths[stage.name]).as_posix()
            parts.append(f"\\copy {stage.name} FROM '{path}' WITH (FORMAT csv, HEADER true)")
        parts.append("")

        if self.guards:
            checks = []
            for guard in self.guards:
                safe_message = guard.message.replace("'", "''")
                checks.append(
                    f"  IF {guard.fail_when} THEN\n"
                    f"    RAISE EXCEPTION '{safe_message}';\n"
                    f"  END IF;"
                )
            body = "\n".join(checks)
            parts.append(f"DO $guards$\nBEGIN\n{body}\nEND $guards$;")
            parts.append("")

        for statement in self.statements:
            parts.append(statement.rstrip().rstrip(";") + ";")
            parts.append("")

        for metric in self.metrics:
            parts.append(
                f"SELECT '{metric.name}' AS metric, ({metric.sql}) AS value;"
            )
        if self.metrics:
            parts.append("")

        parts.append("ROLLBACK;" if rollback else "COMMIT;")
        return "\n".join(parts) + "\n"

    def run(self, apply=False):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            staged_paths = {}
            for stage in self.stages:
                path = temp / f"{stage.name}.csv"
                preview.write_csv(path, stage.rows, stage.csv_fields())
                staged_paths[stage.name] = path
            sql = self.build_sql(staged_paths, rollback=not apply)
            stdout, stderr = db.run_sql(sql)
        return LoadResult(applied=apply, stdout=stdout, stderr=stderr)


@dataclass
class LoadResult:
    applied: bool
    stdout: str
    stderr: str

    def report(self):
        if self.stdout.strip():
            print(self.stdout.strip())
        if self.stderr.strip():
            print(self.stderr.strip())
        print("Committed." if self.applied else "Dry run complete. Transaction rolled back.")


def loader_cli(description, build_load, extra_args=None):
    """Standard CLI for a loader pipeline.

    `build_load(args)` returns a GuardedLoad. Dry run is the default; --apply
    commits.
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--apply", action="store_true", help="Commit the transaction; default is rollback.")
    parser.add_argument("--preview-dir", default=None, help="Override the preview directory.")
    for args, kwargs in (extra_args or []):
        parser.add_argument(*args, **kwargs)
    parsed = parser.parse_args()

    try:
        load = build_load(parsed)
        result = load.run(apply=parsed.apply)
    except preview.PreviewError as exc:
        print(f"Preview validation failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except db.PsqlError as exc:
        # A tripped guard is an expected outcome, not a crash -- print what
        # the database said instead of a traceback.
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    result.report()
    return result
