"""Export/load split availability curation as repo-committed CSVs.

split_gates and curated_availability are durable human data (which split a
gate, location, area, table or trainer opens in), but they live in one
database. Their portable form is etl/curation_data/vg{N}_gates.csv and
vg{N}_availability.csv: export after curating on dev, commit, and load on
any other database. Loading upserts by primary key; rows absent from the
CSV are left alone.

    python -m etl.pipelines.sync_curated_availability export --version-group-id 1001
    python -m etl.pipelines.sync_curated_availability load --version-group-id 1001 --apply
"""
import argparse
import csv
import sys
from pathlib import Path

from .. import db

DATA_DIR = Path(__file__).resolve().parent.parent / "curation_data"
GATE_COLUMNS = ["version_group_id", "gate_key", "label", "opens_in", "default_methods", "sort_order", "note", "source"]
RULE_COLUMNS = ["version_group_id", "subject_kind", "subject_key", "opens_in", "gate_key", "note", "source"]


def gates_path(version_group_id):
    return DATA_DIR / f"vg{int(version_group_id)}_gates.csv"


def rules_path(version_group_id):
    return DATA_DIR / f"vg{int(version_group_id)}_availability.csv"


def _copy_out(sql, path):
    one_line = " ".join(sql.split())
    stdout, _ = db.run_sql(f"\\copy ({one_line}) to stdout with (format csv, header)")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(stdout)
    return max(0, len(stdout.splitlines()) - 1)


def export(version_group_id):
    vg = int(version_group_id)
    gates = _copy_out(f"""
SELECT version_group_id, gate_key, label, opens_in,
       array_to_string(default_methods, ',') AS default_methods, sort_order, note, source
FROM split_gates WHERE version_group_id = {vg} ORDER BY sort_order, gate_key
""", gates_path(vg))
    rules = _copy_out(f"""
SELECT version_group_id, subject_kind, subject_key, opens_in, gate_key, note, source
FROM curated_availability WHERE version_group_id = {vg} ORDER BY subject_kind, subject_key
""", rules_path(vg))
    print(f"exported {gates} gates to {gates_path(vg)} and {rules} rules to {rules_path(vg)}")


def _text(value):
    if value is None or value == "":
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def _int(value, default="NULL"):
    text = (value or "").strip()
    return str(int(text)) if text else default


def _methods(value):
    keys = [k.strip() for k in (value or "").split(",") if k.strip()]
    return "ARRAY[" + ", ".join(_text(k) for k in keys) + "]::text[]" if keys else "'{}'::text[]"


def _read(path, version_group_id):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    bad = [r for r in rows if int(r["version_group_id"]) != int(version_group_id)]
    if bad:
        print(f"{len(bad)} rows in {path} carry a different version_group_id", file=sys.stderr)
        raise SystemExit(1)
    return rows


def load(version_group_id, apply_changes):
    vg = int(version_group_id)
    gates = _read(gates_path(vg), vg)
    rules = _read(rules_path(vg), vg)
    if not gates and not rules:
        print(f"no availability CSVs for version group {vg} under {DATA_DIR}", file=sys.stderr)
        raise SystemExit(1)
    statements = ["BEGIN;"]
    if gates:
        values = ",\n".join(
            f"({vg}, {_text(r['gate_key'])}, {_text(r['label'])}, {_text(r.get('opens_in'))}, "
            f"{_methods(r.get('default_methods'))}, {_int(r.get('sort_order'), '0')}, {_text(r.get('note'))}, {_text(r.get('source'))})"
            for r in gates)
        statements.append(f"""
INSERT INTO split_gates (version_group_id, gate_key, label, opens_in, default_methods, sort_order, note, source)
VALUES
{values}
ON CONFLICT (version_group_id, gate_key) DO UPDATE SET
  label = excluded.label, opens_in = excluded.opens_in, default_methods = excluded.default_methods,
  sort_order = excluded.sort_order, note = excluded.note, source = excluded.source;""")
    if rules:
        values = ",\n".join(
            f"({vg}, {_text(r['subject_kind'])}, {_text(r['subject_key'])}, {_text(r.get('opens_in'))}, "
            f"{_text(r.get('gate_key'))}, {_text(r.get('note'))}, {_text(r.get('source'))})"
            for r in rules)
        statements.append(f"""
INSERT INTO curated_availability (version_group_id, subject_kind, subject_key, opens_in, gate_key, note, source)
VALUES
{values}
ON CONFLICT (version_group_id, subject_kind, subject_key) DO UPDATE SET
  opens_in = excluded.opens_in, gate_key = excluded.gate_key, note = excluded.note,
  source = excluded.source, decided_at = current_timestamp;""")
    statements.append(f"SELECT 'gates' AS metric, (SELECT count(*) FROM split_gates WHERE version_group_id = {vg}) AS value;")
    statements.append(f"SELECT 'rules' AS metric, (SELECT count(*) FROM curated_availability WHERE version_group_id = {vg}) AS value;")
    statements.append("COMMIT;" if apply_changes else "ROLLBACK;")
    try:
        stdout, stderr = db.run_sql("\n".join(statements))
    except db.PsqlError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    print(stdout.strip())
    if stderr.strip():
        print(stderr.strip())
    print("Committed." if apply_changes else "Dry run complete. Transaction rolled back.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["export", "load"])
    parser.add_argument("--version-group-id", type=int, required=True)
    parser.add_argument("--apply", action="store_true", help="load: commit; default is a dry run.")
    args = parser.parse_args()
    if args.command == "export":
        export(args.version_group_id)
    else:
        load(args.version_group_id, args.apply)


if __name__ == "__main__":
    main()
