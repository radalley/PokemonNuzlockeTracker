import csv
import html
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREVIEW_DIR = ROOT / "black2white2_build6_preview"
INDEX_URL = "https://www.serebii.net/pokearth/unova/"
USER_AGENT = "Lockley trainer data research/1.0"


def normalize(value):
    value = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    value = value.lower().replace("pokémon", "pkmn").replace("pokemon", "pkmn")
    return re.sub(r"[^a-z0-9]+", "", value)


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("latin-1", errors="replace")


def page_links(index_html):
    links = set()
    for href in re.findall(r'href=["\']([^"\']+\.shtml)["\']', index_html, re.I):
        url = urllib.parse.urljoin(INDEX_URL, html.unescape(href))
        if "/pokearth/unova/" in url:
            links.add(url)
    return sorted(links)


def trainer_records(page_html):
    marker = re.search(r'<a\s+name=["\']trainers-bw2["\']', page_html, re.I)
    if not marker:
        return []
    section = page_html[marker.start():]
    end = re.search(r'<a\s+name=["\']items', section, re.I)
    if end:
        section = section[:end.start()]
    records = []
    starts = [match.start() for match in re.finditer(r'<table\s+class=["\']trainer["\']', section, re.I)]
    for index, start in enumerate(starts):
        table = section[start:starts[index + 1] if index + 1 < len(starts) else len(section)]
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.I | re.S)
        if len(rows) < 2:
            continue
        cells = re.findall(r"<td[^>]*>(.*?)</td>", rows[1], re.I | re.S)
        if not cells:
            continue
        label = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", cells[0]))).strip()
        species = []
        for cell in cells[1:]:
            match = re.search(r'<a[^>]+href=["\']/pokedex-bw/\d+\.shtml["\'][^>]*>(.*?)</a>', cell, re.I | re.S)
            if match:
                species.append(html.unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip())
        levels = [int(value) for value in re.findall(r'class=["\']level["\'][^>]*>\s*Level\s+(\d+)', table, re.I)]
        if label:
            records.append({"label": label, "party": sorted(zip(map(normalize, species), levels))})
    return records


def location_name(page_html, url):
    title = re.search(r"<title>(.*?)\s+-\s+Unova\s+-", page_html, re.I | re.S)
    if title:
        return html.unescape(re.sub(r"<[^>]+>", "", title.group(1))).strip()
    return Path(urllib.parse.urlparse(url).path).stem


def trainer_key(row):
    trainer_class = re.sub(r"^TRAINER_CLASS_", "", row["trainer_class"])
    return normalize(trainer_class + row["trainer_name"])


def label_candidates(record, trainers, parties):
    label = record["label"]
    key = normalize(label)
    name_matches = []
    for row in trainers:
        name = normalize(row["trainer_name"])
        if name and key.endswith(name):
            name_matches.append(row)
    class_matches = []
    for row in name_matches:
        trainer_class = normalize(re.sub(r"^TRAINER_CLASS_", "", row["trainer_class"]))
        if trainer_class in key:
            class_matches.append(row)
    matches = class_matches or name_matches
    if record["party"]:
        exact = [row for row in matches if parties[row["encounter_name"]] == record["party"]]
        if exact:
            matches = exact
    return matches


def main():
    with (PREVIEW_DIR / "trainer_pool_preview.csv").open(encoding="utf-8", newline="") as handle:
        trainers = list(csv.DictReader(handle))
    parties = defaultdict(list)
    with (PREVIEW_DIR / "trainer_pokemon_preview.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            parties[row["encounter_name"]].append((normalize(row["species_name"]), int(row["lvl"])))
    parties = {key: sorted(value) for key, value in parties.items()}

    index_html = fetch(INDEX_URL)
    links = page_links(index_html)
    pages = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch, url): url for url in links}
        for future in as_completed(futures):
            url = futures[future]
            pages.append((url, future.result()))
            time.sleep(0.02)

    matches = defaultdict(list)
    unmatched = []
    ambiguous = []
    for url, page_html in sorted(pages):
        location = location_name(page_html, url)
        for record in trainer_records(page_html):
            label = record["label"]
            candidates = label_candidates(record, trainers, parties)
            if len(candidates) == 1:
                matches[candidates[0]["encounter_name"]].append((location, label, url))
            elif not candidates:
                unmatched.append({"location": location, "trainer_label": label, "source_url": url})
            else:
                ambiguous.append({
                    "location": location,
                    "trainer_label": label,
                    "encounter_names": ",".join(row["encounter_name"] for row in candidates),
                    "source_url": url,
                })

    resolved = []
    for encounter_name, refs in sorted(matches.items()):
        locations = sorted({ref[0] for ref in refs})
        if len(locations) == 1:
            resolved.append({
                "encounter_name": encounter_name,
                "location_name": locations[0],
                "trainer_label": refs[0][1],
                "source_url": refs[0][2],
            })
        else:
            ambiguous.append({
                "location": ",".join(locations),
                "trainer_label": refs[0][1],
                "encounter_names": encounter_name,
                "source_url": ",".join(sorted({ref[2] for ref in refs})),
            })

    outputs = [
        ("serebii_location_matches.csv", resolved, ["encounter_name", "location_name", "trainer_label", "source_url"]),
        ("serebii_location_unmatched.csv", unmatched, ["location", "trainer_label", "source_url"]),
        ("serebii_location_ambiguous.csv", ambiguous, ["location", "trainer_label", "encounter_names", "source_url"]),
    ]
    for filename, rows, fields in outputs:
        with (PREVIEW_DIR / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    print(f"pages: {len(pages)}")
    print(f"resolved trainer locations: {len(resolved)}")
    print(f"unmatched labels: {len(unmatched)}")
    print(f"ambiguous labels: {len(ambiguous)}")


if __name__ == "__main__":
    main()
