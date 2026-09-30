"""Blaze Black / Volt White ETL (version group 1001, load build 7).

Sources are Drayano's documentation for Blaze Black & Volt White 3.1,
converted from RTF to UTF-8 text and placed in
LOCKLEY_ETL_SOURCE_DIR/blazeblack/ (the docs stay out of the repo). The RTF
conversion is a one-time PowerShell step; see docs in etl/README.md.

Run `python -m etl.pipelines.blazeblack.build_previews` to parse everything
into blazeblack_build7_preview/, then load with the standard loaders.
"""
