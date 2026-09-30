"""Load a hack's species/learnset override previews.

    python -m etl.pipelines.load_species_overrides blazeblack           # dry run
    python -m etl.pipelines.load_species_overrides blazeblack --apply

Loads five override sets keyed at the hack's version group: species
abilities / stats / types (rows the generation patch join prefers when the
run's version group matches), materialized level-up learnsets (movesets),
and rebalanced move data (moves). Guards refuse if the version group
already has rows in any target table.
"""
from .. import manifests, preview
from ..loader import Guard, GuardedLoad, Metric, StageTable, loader_cli

STAGES = {
    "species_abilities": [
        ("species_id", "integer"), ("generation", "text"),
        ("ability1", "text"), ("ability2", "text"), ("ability3", "text"),
        ("version_group_id", "integer"),
    ],
    "species_stats": [
        ("species_id", "integer"), ("generation", "text"), ("bst", "integer"),
        ("hp", "integer"), ("atk", "integer"), ("def", "integer"),
        ("spa", "integer"), ("spd", "integer"), ("spe", "integer"),
        ("version_group_id", "integer"),
    ],
    "species_types": [
        ("species_id", "integer"), ("generation", "text"),
        ("type1", "text"), ("type2", "text"), ("version_group_id", "integer"),
    ],
    "movesets": [
        ("species_id", "integer"), ("move_id", "integer"), ("learn_method", "text"),
        ("learn_level", "integer"), ("version_group_id", "integer"),
    ],
    "moves": [
        ("move_id", "integer"), ("move_name", "text"), ("type", "text"),
        ("damage_class", "text"), ("power", "text"), ("accuracy", "text"),
        ("version_group_id", "integer"),
    ],
}

INSERTS = {
    "species_abilities": """
INSERT INTO species_abilities (ability_pk, species_id, generation, ability1, ability2, ability3, version_group_id)
SELECT (SELECT coalesce(max(ability_pk), 0) FROM species_abilities) + row_number() OVER (ORDER BY species_id),
       species_id, nullif(generation, '')::integer, nullif(ability1, ''), nullif(ability2, ''),
       nullif(ability3, ''), version_group_id
FROM species_abilities_stage
""",
    "species_stats": """
INSERT INTO species_stats (species_id, generation, bst, hp, atk, def, spa, spd, spe, version_group_id)
SELECT species_id, nullif(generation, '')::integer, bst, hp, atk, def, spa, spd, spe, version_group_id
FROM species_stats_stage ORDER BY species_id
""",
    "species_types": """
INSERT INTO species_types (species_id, generation, type1, type2, version_group_id)
SELECT species_id, nullif(generation, '')::integer, nullif(type1, ''), nullif(type2, ''), version_group_id
FROM species_types_stage ORDER BY species_id
""",
    "movesets": """
INSERT INTO movesets (species_id, move_id, learn_method, learn_level, version_group_id)
SELECT species_id, move_id, learn_method, learn_level, version_group_id
FROM movesets_stage ORDER BY species_id, learn_level, move_id
""",
    "moves": """
INSERT INTO moves (move_id, move_name, type, damage_class, power, accuracy, version_group_id)
SELECT move_id, nullif(move_name, ''), nullif(type, ''), nullif(damage_class, ''),
       nullif(power, '')::integer, nullif(accuracy, '')::integer, version_group_id
FROM moves_stage ORDER BY move_id
""",
}


def build_load(args):
    manifest = manifests.load(args.manifest)
    preview_dir = args.preview_dir or manifest.preview_dir()
    vg = manifest.version_group_id

    stages, guards, statements, metrics = [], [], [], []
    for name, columns in STAGES.items():
        rows = preview.read_csv(f"{preview_dir}/{name}_override_preview.csv")
        expected = manifest.expected(f"override_{name}")
        preview.expect_row_count(rows, expected, name)
        preview.expect_column_value(rows, "version_group_id", vg, name)
        stages.append(StageTable(f"{name}_stage", columns, rows))
        guards.append(Guard(
            f"EXISTS (SELECT 1 FROM {name} WHERE version_group_id = {vg})",
            f"{name} already has rows for version group {vg}",
        ))
        guards.append(Guard(
            f"(SELECT count(*) FROM {name}_stage) <> {len(rows)}",
            f"Unexpected {name} stage row count",
        ))
        statements.append(INSERTS[name])
        metrics.append(Metric(
            f"{name}_rows",
            f"SELECT count(*) FROM {name} WHERE version_group_id = {vg}",
        ))

    guards += [
        Guard(
            "EXISTS (SELECT 1 FROM species_abilities_stage s "
            "LEFT JOIN species sp ON sp.species_id = s.species_id WHERE sp.species_id IS NULL)",
            "An ability override references an unknown species",
        ),
        Guard(
            "EXISTS (SELECT 1 FROM movesets_stage s "
            "LEFT JOIN species sp ON sp.species_id = s.species_id WHERE sp.species_id IS NULL)",
            "A learnset override references an unknown species",
        ),
        Guard(
            "EXISTS (SELECT 1 FROM movesets_stage s WHERE NOT EXISTS ("
            "SELECT 1 FROM moves m WHERE m.move_id = s.move_id))",
            "A learnset override references an unknown move",
        ),
    ]

    return GuardedLoad(
        title=f"{manifest.label} species/learnset overrides",
        stages=stages, guards=guards, statements=statements, metrics=metrics,
    )


def main():
    loader_cli(
        "Load a hack's species/learnset override previews.",
        build_load,
        extra_args=[(("manifest",), {"help": "Manifest key, e.g. blazeblack"})],
    )


if __name__ == "__main__":
    main()
