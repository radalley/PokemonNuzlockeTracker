"""Deprecated alias: superseded by the generic load_trainers pipeline.

    python -m etl.pipelines.load_trainers blackwhite --apply
"""
from .load_trainers import build_load, main  # noqa: F401

if __name__ == "__main__":
    main()
