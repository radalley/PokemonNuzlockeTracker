import csv
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "Frontend" / "public" / "sprites" / "trainers" / "gen5"
MANIFEST = OUT_DIR / "gen5_sprite_manifest.csv"
API_URL = "https://archives.bulbagarden.net/w/api.php"
CATEGORY = "Category:Generation V Trainer sprites"
USER_AGENT = "Lockley local data loader/1.0 (trainer sprite import)"


def request_json(params):
    request = urllib.request.Request(
        f"{API_URL}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def category_files():
    files = []
    continuation = {}
    while True:
        params = {
            "action": "query",
            "format": "json",
            "generator": "categorymembers",
            "gcmtitle": CATEGORY,
            "gcmtype": "file",
            "gcmlimit": "500",
            "prop": "imageinfo",
            "iiprop": "url",
        }
        params.update(continuation)
        data = request_json(params)
        for page in data.get("query", {}).get("pages", {}).values():
            title = page.get("title", "").removeprefix("File:")
            image_info = page.get("imageinfo") or []
            if title and image_info:
                files.append({"title": title, "url": image_info[0]["url"]})
        if "continue" not in data:
            return sorted(files, key=lambda row: row["title"])
        continuation = data["continue"]


def identifier(value):
    value = value.replace("Pokémon", "Pokemon").replace("Poké", "Poke")
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()


def alias_name(title):
    stem = Path(title).stem
    match = re.fullmatch(r"Spr (BW|B2W2) (.+)", stem)
    if not match or match.group(2).lower().endswith(" back"):
        return ""
    game, label = match.groups()
    return f"TRAINER_PIC_{game}_{identifier(label)}.png"


def download(url, destination):
    if destination.exists() and destination.stat().st_size:
        return False
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        destination.write_bytes(response.read())
    time.sleep(0.05)
    return True


def write_static_alias(source, destination):
    with Image.open(source) as image:
        image.seek(image.n_frames - 1)
        image.convert("RGBA").save(destination, format="PNG", optimize=True)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    downloaded = 0
    aliases = 0
    for file_info in category_files():
        title = file_info["title"]
        stored_name = title.replace(" ", "_")
        stored_path = OUT_DIR / stored_name
        downloaded += download(file_info["url"], stored_path)

        alias = alias_name(title)
        if alias:
            alias_path = OUT_DIR / alias
            if not alias_path.exists():
                write_static_alias(stored_path, alias_path)
                aliases += 1
        rows.append(
            {
                "source_title": title,
                "source_url": file_info["url"],
                "stored_file": stored_name,
                "lockley_alias": alias,
            }
        )

    with MANIFEST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source_title", "source_url", "stored_file", "lockley_alias"],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"category files: {len(rows)}")
    print(f"downloaded originals: {downloaded}")
    print(f"created aliases: {aliases}")
    print(f"manifest: {MANIFEST}")


if __name__ == "__main__":
    main()
