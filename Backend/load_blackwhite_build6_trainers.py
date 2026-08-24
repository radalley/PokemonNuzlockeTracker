"""Deprecated: superseded by etl.pipelines.gen5_trainers.

Kept so existing commands keep working. Prefer:

    python -m etl.pipelines.gen5_trainers blackwhite --apply
"""
import sys

from etl.pipelines import gen5_trainers

MANIFEST = "blackwhite"


def main():
    print(
        f"NOTE: this script is deprecated; use "
        f"'python -m etl.pipelines.gen5_trainers {MANIFEST}' instead.",
        file=sys.stderr,
    )
    sys.argv = [sys.argv[0], MANIFEST, *sys.argv[1:]]
    gen5_trainers.main()


if __name__ == "__main__":
    main()
