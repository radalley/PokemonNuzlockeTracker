"""Re-apply curated placement decisions to trainer_pool.

Loaders run this inside their own transaction; this standalone form covers
every other path that touches trainer rows (manual fixes, legacy loaders).

    python -m etl.pipelines.apply_curated_placements --version-group-id 11 --apply
"""
import argparse
import sys

from .. import curation, db


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version-group-id", type=int, required=True)
    parser.add_argument("--apply", action="store_true", help="Commit; default is a dry run.")
    args = parser.parse_args()

    finish = "COMMIT;" if args.apply else "ROLLBACK;"
    sql = (
        "BEGIN;\n"
        + curation.apply_curated_placements_sql(args.version_group_id)
        + ";\n"
        + f"SELECT 'curated_placements' AS metric, ({curation.curated_metric_sql(args.version_group_id)}) AS value;\n"
        + f"{finish}\n"
    )
    try:
        stdout, stderr = db.run_sql(sql)
    except db.PsqlError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    print(stdout.strip())
    if stderr.strip():
        print(stderr.strip())
    print("Committed." if args.apply else "Dry run complete. Transaction rolled back.")


if __name__ == "__main__":
    main()
