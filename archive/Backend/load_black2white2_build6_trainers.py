"""Deprecated: superseded by etl.pipelines.gen5_trainers.

Previously a shim that monkey-patched module constants on the Black/White
loader, which left Black/White wording in this game's help text and error
messages. Prefer:

    python -m etl.pipelines.gen5_trainers black2white2 --apply
"""
import sys

from etl.pipelines import gen5_trainers

MANIFEST = "black2white2"


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
