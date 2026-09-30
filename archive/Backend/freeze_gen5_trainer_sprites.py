import csv
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
SPRITE_DIR = ROOT / "Frontend" / "public" / "sprites" / "trainers" / "gen5"
MANIFEST = SPRITE_DIR / "gen5_sprite_manifest.csv"


def main():
    with MANIFEST.open("r", newline="", encoding="utf-8") as handle:
        manifest = [row for row in csv.DictReader(handle) if row["lockley_alias"]]

    animated_sources = 0
    for row in manifest:
        source = SPRITE_DIR / row["stored_file"]
        destination = SPRITE_DIR / row["lockley_alias"]
        with Image.open(source) as image:
            animated_sources += image.n_frames > 1
            image.seek(image.n_frames - 1)
            image.convert("RGBA").save(destination, format="PNG", optimize=True)

    aliases = sorted(SPRITE_DIR.glob("TRAINER_PIC_*.png"))
    remaining = [path for path in aliases if b"acTL" in path.read_bytes()]
    if remaining:
        raise RuntimeError(f"Animated aliases remain: {len(remaining)}")
    print(f"Gen V aliases checked: {len(aliases)}")
    print(f"Animated sources frozen at final frame: {animated_sources}")
    print("Animated aliases remaining: 0")


if __name__ == "__main__":
    main()
