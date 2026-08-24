"""Normalization of decomp/ROM constants into the shapes the database stores.

Sources disagree about spelling: the Gen 1-4 decomps emit `ITEM_ORAN_BERRY`
and `MOVE_GRASS_WHISTLE`, the Gen 5 ROM text banks emit display names like
`Oran Berry`, and ROM hack documentation emits era-specific text such as
`GrassWhistle` or `NidoranM`. Everything that reconciles those lives here so
a new source only has to declare its quirks, not reimplement the rules.
"""
import re

CONSTANT_PREFIXES = ("ITEM_", "MOVE_", "ABILITY_", "SPECIES_", "TRAINER_CLASS_", "TRAINER_")

# Names whose canonical `species.name` spelling can't be derived mechanically.
SPECIES_ALIASES = {
    "nidoranm": "nidoran-m",
    "nidoranf": "nidoran-f",
    "nidoran♂": "nidoran-m",
    "nidoran♀": "nidoran-f",
    "mrmime": "mr-mime",
    "mr.mime": "mr-mime",
    "mimejr": "mime-jr",
    "mimejr.": "mime-jr",
    "farfetchd": "farfetchd",
    "farfetch'd": "farfetchd",
    "hooh": "ho-oh",
    "porygonz": "porygon-z",
    "porygon2": "porygon2",
    "typenull": "type-null",
    "jangmoo": "jangmo-o",
    "hakamoo": "hakamo-o",
    "kommoo": "kommo-o",
    "flabebe": "flabebe",
    "deoxys": "deoxys-normal",
    "giratina": "giratina-altered",
    "shaymin": "shaymin-land",
    "tornadus": "tornadus-incarnate",
    "thundurus": "thundurus-incarnate",
    "landorus": "landorus-incarnate",
    "keldeo": "keldeo-ordinary",
    "meloetta": "meloetta-aria",
    "basculin": "basculin-red-striped",
    "darmanitan": "darmanitan-standard",
    "meowstic": "meowstic-male",
    "aegislash": "aegislash-shield",
    "pumpkaboo": "pumpkaboo-average",
    "gourgeist": "gourgeist-average",
    "wormadam": "wormadam-plant",
    "lycanroc": "lycanroc-midday",
    "wishiwashi": "wishiwashi-solo",
    "minior": "minior-red-meteor",
    "mimikyu": "mimikyu-disguised",
    "toxtricity": "toxtricity-amped",
    "eiscue": "eiscue-ice",
    "indeedee": "indeedee-male",
    "urshifu": "urshifu-single-strike",
    "zacian": "zacian-hero",
    "zamazenta": "zamazenta-hero",
}


def strip_constant_prefix(token):
    """`ITEM_ORAN_BERRY` -> `ORAN_BERRY`; leaves unprefixed tokens alone."""
    token = (token or "").strip()
    for prefix in CONSTANT_PREFIXES:
        if token.startswith(prefix):
            return token[len(prefix):]
    return token


def to_slug(token):
    """Normalize any source spelling to the lowercase hyphenated database form.

    `MOVE_GRASS_WHISTLE`, `GrassWhistle`, and `Grass Whistle` all become
    `grass-whistle`.
    """
    token = strip_constant_prefix(token)
    if not token:
        return ""
    token = token.replace("_", " ").replace("-", " ")
    # Split camel/Pascal case that older docs use ("GrassWhistle").
    if " " not in token.strip():
        token = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", token)
    token = re.sub(r"[^\w\s]", "", token, flags=re.UNICODE)
    token = re.sub(r"\s+", " ", token).strip().lower()
    return token.replace(" ", "-")


def species_slug(token):
    """Normalize a species name, applying the alias table for irregular forms."""
    raw = strip_constant_prefix(token or "").strip().lower()
    compact = re.sub(r"[^a-z0-9♂♀.']", "", raw)
    if compact in SPECIES_ALIASES:
        return SPECIES_ALIASES[compact]
    return to_slug(token)


def split_list(value, separator=","):
    """Split a comma-joined constant list, dropping blanks and NONE sentinels."""
    if not value:
        return []
    tokens = []
    for raw in str(value).split(separator):
        token = raw.strip()
        if not token:
            continue
        if strip_constant_prefix(token).upper() in ("NONE", "NULL", "-"):
            continue
        tokens.append(token)
    return tokens


def fix_mojibake(text):
    """Repair UTF-8 bytes that were decoded as cp1252 (common in RTF exports)."""
    if not text:
        return text
    if not any(marker in text for marker in ("â€", "Ã", "Â")):
        return text
    try:
        return text.encode("cp1252", errors="strict").decode("utf-8", errors="strict")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


PUNCTUATION_FOLD = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"',
    "–": "-", "—": "-", "−": "-",
    "…": "...", " ": " ",
}


def fold_punctuation(text):
    """Replace typographic punctuation with ASCII equivalents.

    Separate from `fix_mojibake`, which only repairs a decoding error: a
    document can legitimately contain curly quotes with no mojibake at all.
    """
    if not text:
        return text
    for fancy, plain in PUNCTUATION_FOLD.items():
        text = text.replace(fancy, plain)
    return text


def clean_text(text):
    """Repair mojibake, then fold punctuation to ASCII."""
    return fold_punctuation(fix_mojibake(text))


def title_key(title):
    """Normalize an encounter title for matching (collapse whitespace, lowercase)."""
    return re.sub(r"\s+", " ", (title or "").strip().lower())
