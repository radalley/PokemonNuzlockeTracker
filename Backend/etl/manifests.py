"""Per-version-group pipeline manifests.

A manifest declares everything about one data set that used to live as module
constants scattered across a generation's scripts: which version group and
games it targets, which load build it writes, where its source data comes
from, and the row counts its preview must match.

Manifests are JSON in `etl/manifests/` so a new data set -- including a ROM
hack -- is a new file rather than a new dialect of script.
"""
import json
from pathlib import Path

from . import config

MANIFEST_DIR = Path(__file__).resolve().parent / "manifests"


class ManifestError(RuntimeError):
    """A manifest is missing or malformed."""


class Manifest:
    def __init__(self, data, path):
        self.path = path
        self._data = data
        for required in ("key", "label", "version_group_id", "load_build"):
            if required not in data:
                raise ManifestError(f"{path.name} is missing required field '{required}'")

    @property
    def key(self):
        return self._data["key"]

    @property
    def label(self):
        return self._data["label"]

    @property
    def version_group_id(self):
        return int(self._data["version_group_id"])

    @property
    def load_build(self):
        return int(self._data["load_build"])

    @property
    def generation(self):
        value = self._data.get("generation")
        return int(value) if value is not None else None

    @property
    def game_ids(self):
        """Mapping of game name -> game_id for the games in this version group."""
        return {k: int(v) for k, v in (self._data.get("game_ids") or {}).items()}

    @property
    def base(self):
        """For a ROM hack: the manifest key of the game it modifies."""
        return self._data.get("base")

    @property
    def is_rom_hack(self):
        return bool(self._data.get("is_rom_hack", False))

    @property
    def source(self):
        """Source descriptor: {'type': 'nds_rom'|'decomp'|'docs', ...}."""
        return self._data.get("source") or {}

    def source_root(self):
        """Resolve this manifest's source root from environment config."""
        source_type = self.source.get("type")
        roots = {
            "nds_rom": config.roms_dir,
            "decomp": config.decomps_dir,
            "docs": config.source_dir,
        }
        if source_type not in roots:
            raise ManifestError(
                f"{self.path.name} has unknown source type {source_type!r}; "
                f"expected one of {sorted(roots)}"
            )
        root = roots[source_type]()
        relative = self.source.get("path")
        return root / relative if relative else root

    def preview_dir(self):
        name = self._data.get("preview_dir") or f"{self.key}_build{self.load_build}_preview"
        return config.preview_dir(name)

    def expected(self, name, default=None):
        """An expected row count from the manifest's `expected` block."""
        return (self._data.get("expected") or {}).get(name, default)

    def get(self, name, default=None):
        return self._data.get(name, default)

    def __repr__(self):
        return f"<Manifest {self.key} vg={self.version_group_id} build={self.load_build}>"


def load(key):
    path = MANIFEST_DIR / f"{key}.json"
    if not path.exists():
        available = ", ".join(sorted(p.stem for p in MANIFEST_DIR.glob("*.json")))
        raise ManifestError(f"No manifest '{key}'. Available: {available or '(none)'}")
    # utf-8-sig tolerates a BOM from Windows-side editors.
    return Manifest(json.loads(path.read_text(encoding="utf-8-sig")), path)


def all_manifests():
    return [load(p.stem) for p in sorted(MANIFEST_DIR.glob("*.json"))]
