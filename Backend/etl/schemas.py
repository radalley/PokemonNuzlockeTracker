"""Single source of truth for the staged column lists.

The `trainer_pool`, `trainer_pokemon`, and `event_bosses` field lists were
previously spelled out in six places each (preview builders, loaders, and the
temp-table DDL), which is how the Crystal loader ended up silently dropping
`slot` from its insert. Pipelines import these instead.
"""

TRAINER_POOL_COLUMNS = [
    ("encounter_name", "text"),
    ("trainer_name", "text"),
    ("trainer_class", "text"),
    ("canonical_location_id", "text"),
    ("is_rematch", "text"),
    ("is_event", "text"),
    ("trainer_items", "text"),
    ("trainer_pic", "text"),
    ("trainer_double", "text"),
    ("details", "text"),
    ("version_group_id", "integer"),
    ("load_build", "integer"),
    ("game_id", "text"),
]

TRAINER_POKEMON_COLUMNS = [
    ("encounter_name", "text"),
    ("species_name", "text"),
    ("lvl", "integer"),
    ("moves", "text"),
    ("held_item", "text"),
    ("iv", "integer"),
    ("version_group_id", "integer"),
    ("load_build", "integer"),
    ("slot", "integer"),
    ("ability", "text"),
    ("ability_clean", "text"),
    ("nature", "text"),
]

EVENT_BOSS_COLUMNS = [
    ("trainer_id", "integer"),
    ("trainer_index", "integer"),
    ("encounter_name", "text"),
    ("trainer_name", "text"),
    ("sort_order", "text"),
    ("encounter_title", "text"),
    ("starter", "text"),
    ("type_focus", "text"),
    ("version_group_id", "integer"),
    ("event_type", "text"),
    ("game_id", "text"),
    ("badge_id", "text"),
]


def names(columns):
    return [name for name, _ in columns]


def subset(columns, available):
    """Restrict a column list to the fields a preview actually provides.

    Older previews predate the WP1 ability/nature columns, so a pipeline can
    stage only what its CSV carries without failing the copy.
    """
    available = set(available)
    return [(name, sql_type) for name, sql_type in columns if name in available]


# A trainer is shown on a location's trainer panel only when it is placed and
# is not a rematch. Duplicated as raw SQL in three loaders before this.
DISPLAYABLE_TRAINER_SQL = (
    "nullif(canonical_location_id, '') IS NOT NULL "
    "AND lower(coalesce(is_rematch, '')) NOT IN ('true', 't', '1', 'yes')"
)
