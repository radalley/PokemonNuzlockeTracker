"""Preview CSV read/write and validation helpers.

Every pipeline emits preview CSVs before anything touches the database, so a
human (or a diff) can inspect exactly what would be loaded. Loaders then read
those same files back.
"""
import csv
import json
from pathlib import Path


class PreviewError(ValueError):
    """A preview file failed validation before load."""


def read_csv(path):
    path = Path(path)
    if not path.exists():
        raise PreviewError(f"Preview file not found: {path}")
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_summary(path, summary):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return path


def expect_row_count(rows, expected, label):
    if expected is not None and len(rows) != expected:
        raise PreviewError(f"Expected {expected} {label} rows, found {len(rows)}")


def expect_column_value(rows, column, expected, label):
    """Every row's `column` must equal `expected` (compared as strings)."""
    wanted = str(expected)
    bad = [r for r in rows if str(r.get(column, "")) != wanted]
    if bad:
        raise PreviewError(
            f"{len(bad)} {label} rows have {column} != {wanted} "
            f"(first: {bad[0].get(column)!r})"
        )


def expect_column_in(rows, column, allowed, label):
    bad = sorted({str(r.get(column, "")) for r in rows} - {str(a) for a in allowed})
    if bad:
        raise PreviewError(f"{label} rows contain unexpected {column} values: {bad[:5]}")


def expect_unique(rows, column, label):
    values = [r.get(column) for r in rows]
    if len(values) != len(set(values)):
        seen, dupes = set(), set()
        for value in values:
            if value in seen:
                dupes.add(value)
            seen.add(value)
        raise PreviewError(f"Duplicate {column} in {label} preview: {sorted(dupes)[:5]}")


def expect_references(rows, column, known, label, target):
    missing = sorted({r.get(column) for r in rows} - set(known))
    if missing:
        raise PreviewError(f"{label} rows reference unknown {target}: {missing[:5]}")
