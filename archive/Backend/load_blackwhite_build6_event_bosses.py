"""Deprecated: superseded by etl.pipelines.gen5_event_bosses.

Kept so existing commands keep working. Prefer:

    python -m etl.pipelines.gen5_event_bosses blackwhite --apply
"""
import sys

from etl.pipelines import gen5_event_bosses

MANIFEST = "blackwhite"


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
