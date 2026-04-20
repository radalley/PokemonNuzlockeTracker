import requests
import json
from pathlib import Path
import time

CACHE_DIR = Path("seed_cache/pokemon_stats")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
LOC_CACHE_DIR = Path("seed_cache/locations")
LOC_CACHE_DIR.mkdir(parents=True, exist_ok=True)
LOC_AREA_CACHE_DIR = Path("seed_cache/location_area")
LOC_AREA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
ITEM_CACHE_DIR = Path("seed_cache/item")
ITEM_CACHE_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://pokeapi.co/api/v2/pokemon/"
BASE_LOC_URL = "https://pokeapi.co/api/v2/location/"
BASE_LOC_AREA_URL = "https://pokeapi.co/api/v2/location-area/"
ITEM_URL = "https://pokeapi.co/api/v2/item/"
def download_all_pokemon(start=1, end=151):
    for dex_id in range(start, end + 1):
        cache_path = CACHE_DIR / f"{dex_id}.json"

        if cache_path.exists():
            print(f"#{dex_id} already cached, skipping")
            continue

        url = f"{BASE_URL}{dex_id}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"#{dex_id} {data['name']} saved")
        else:
            print(f"#{dex_id} failed: {response.status_code}")

        time.sleep(0.1)  # be polite to the API

def download_all_locations(start=1, end=3000):
    for loc_id in range(start, end + 1):
        cache_path = LOC_CACHE_DIR / f"{loc_id}.json"

        if cache_path.exists():
            print(f"#{loc_id} already cached, skipping")
            continue

        url = f"{BASE_LOC_URL}{loc_id}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"#{loc_id} {data['name']} saved")
        else:
            print(f"#{loc_id} failed: {response.status_code}")

        time.sleep(0.1)  # be polite to the API
        pass
def download_all_location_areas(start=1, end=40):
    for loc_id in range(start, end + 1):
        cache_path = LOC_AREA_CACHE_DIR / f"{loc_id}.json"

        if cache_path.exists():
            print(f"#{loc_id} already cached, skipping")
            continue

        url = f"{BASE_LOC_AREA_URL}{loc_id}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"#{loc_id} {data['name']} saved")
        else:
            print(f"#{loc_id} failed: {response.status_code}")

        time.sleep(0.1)  # be polite to the API
        pass

def download_all_items(start=1, end=40):
    for item_id in range(start, end + 1):
        cache_path = ITEM_CACHE_DIR / f"{item_id}.json"

        if cache_path.exists():
            print(f"#{item_id} already cached, skipping")
            continue

        url = f"{ITEM_URL}{item_id}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"#{item_id} {data['name']} saved")
        else:
            print(f"#{item_id} failed: {response.status_code}")

        time.sleep(0.1)  # be polite to the API
        pass

# download_all_pokemon(1, 1025)
# download_all_locations()
download_all_location_areas()
download_all_items()

print('done')