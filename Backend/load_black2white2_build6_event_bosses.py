"""Deprecated: superseded by etl.pipelines.gen5_event_bosses.

Previously a shim that monkey-patched module constants on the Black/White
loader. Prefer:

    python -m etl.pipelines.gen5_event_bosses black2white2 --apply
"""
import sys

from etl.pipelines import gen5_event_bosses

MANIFEST = "black2white2"


def main():
    print(
        f"NOTE: this script is deprecated; use "
        f"'python -m etl.pipelines.gen5_event_bosses {MANIFEST}' instead.",
        file=sys.stderr,
    )
    sys.argv = [sys.argv[0], MANIFEST, *sys.argv[1:]]
    gen5_event_bosses.main()


if __name__ == "__main__":
    main()
