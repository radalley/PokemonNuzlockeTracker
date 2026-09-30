"""The canonical encounter-method vocabulary.

Every wild-encounter row carries one of these keys in encounter_pool.method
(the Blaze Black parser maps the doc's labels onto them; a later PokeAPI
loader for vanilla games emits them directly, which is why the keys follow
PokeAPI's names). The API serves the registry alongside the tables so the
frontend never hard-codes a method: it only maps `group` to an icon and a
hue. Keys ending in `-spots` are the rare spots (shaking grass, dust clouds,
rippling water). `static` is a scripted encounter with no wild slot; it is
never part of a table.
"""

METHODS = [
    {"key": "grass", "label": "Tall grass", "group": "grass", "is_rare": False, "sort_order": 10,
     "description": "Ordinary tall grass. Doc: 'Grass, Normal'."},
    {"key": "dark-grass", "label": "Dark grass", "group": "grass", "is_rare": False, "sort_order": 20,
     "description": "Dark tall grass where double battles occur. Doc: 'Grass, Doubles'."},
    {"key": "grass-spots", "label": "Shaking grass", "group": "grass", "is_rare": True, "sort_order": 30,
     "description": "Rustling patches; none appear before the first badge. Doc: 'Grass, Special' / 'Shaking Grass'."},
    {"key": "rocky-grass", "label": "Rocky grass", "group": "grass", "is_rare": False, "sort_order": 40,
     "description": "Grass among rocks on Victory Road's outer path. Doc: 'Rocky Grass'."},
    {"key": "cave", "label": "Cave floor", "group": "cave", "is_rare": False, "sort_order": 50,
     "description": "Walking inside a cave. Doc: 'Cave, Normal'."},
    {"key": "cave-spots", "label": "Dust cloud", "group": "cave", "is_rare": True, "sort_order": 60,
     "description": "Dust clouds on a cave floor. Doc: 'Cave, Special'."},
    {"key": "sand", "label": "Desert sand", "group": "ground", "is_rare": False, "sort_order": 70,
     "description": "Walking on desert sand. Doc: 'Sand'."},
    {"key": "puddle", "label": "Puddle", "group": "ground", "is_rare": False, "sort_order": 80,
     "description": "Marsh puddles around Icirrus. Doc: 'Puddle, Normal'."},
    {"key": "tower", "label": "Tower floor", "group": "indoor", "is_rare": False, "sort_order": 90,
     "description": "Walking on a tower floor. Doc: 'Tower, Normal'."},
    {"key": "floor", "label": "Floor", "group": "indoor", "is_rare": False, "sort_order": 100,
     "description": "The floor of an indoor room. Doc: 'Floor'."},
    {"key": "bridge-spots", "label": "Bridge shadow", "group": "bridge", "is_rare": True, "sort_order": 110,
     "description": "Shadows of Pokémon flying over a bridge. Doc: 'Bridge, Special'."},
    {"key": "surf", "label": "Surfing", "group": "water", "is_rare": False, "sort_order": 120,
     "description": "Surfing on water. Doc: 'Surf, Normal'."},
    {"key": "surf-spots", "label": "Rippling water", "group": "water", "is_rare": True, "sort_order": 130,
     "description": "Rippling spots while surfing. Doc: 'Surf, Special'."},
    {"key": "fish", "label": "Fishing", "group": "fishing", "is_rare": False, "sort_order": 140,
     "description": "Fishing. Doc: 'Fish, Normal'."},
    {"key": "fish-spots", "label": "Rippling fishing", "group": "fishing", "is_rare": True, "sort_order": 150,
     "description": "Fishing in rippling spots. Doc: 'Fish, Special'."},
    {"key": "static", "label": "Static encounter", "group": "special", "is_rare": False, "sort_order": 160,
     "description": "A scripted encounter standing in the world; no wild slot."},
]

METHOD_KEYS = [entry["key"] for entry in METHODS]
SORT_ORDER = {entry["key"]: entry["sort_order"] for entry in METHODS}
SLOT_KINDS = ("slot", "overlay", "static")


def registry():
    """The registry as plain dicts, safe to hand to jsonify."""
    return [dict(entry) for entry in METHODS]
