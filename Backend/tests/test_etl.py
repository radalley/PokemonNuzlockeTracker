"""
WP3 tests: the shared etl package.

These cover the pure logic -- manifest loading, name normalization, preview
validation, and the SQL the loader framework generates. The end-to-end load
itself is exercised against a scratch database by hand (see etl/README.md);
what matters here is that guards are emitted, dry runs roll back, and the
portable trainer binding is actually in the generated SQL.
"""
import pytest

from etl import manifests, normalize, preview, schemas
from etl.loader import Guard, GuardedLoad, Metric, StageTable
from etl.pipelines import gen5_event_bosses, gen5_trainers


# ---------------------------------------------------------------------------
# manifests
# ---------------------------------------------------------------------------

def test_gen5_manifests_declare_expected_shape():
    bw = manifests.load("blackwhite")
    assert bw.version_group_id == 11
    assert bw.load_build == 6
    assert bw.game_ids == {"black": 17, "white": 18}
    assert bw.expected("trainers") == 615
    assert bw.expected("trainer_pokemon") == 1304
    assert bw.expected("event_bosses") == 61

    b2w2 = manifests.load("black2white2")
    assert b2w2.version_group_id == 14
    assert b2w2.game_ids == {"black2": 21, "white2": 22}
    # B2W2 has 4 version-exclusive boss rows (2 per game) even though no
    # trainer_pool row is game-specific.
    assert b2w2.expected("game_specific_bosses") == 4
    assert b2w2.expected("game_specific_trainers") == 0


def test_unknown_manifest_lists_available_ones():
    with pytest.raises(manifests.ManifestError) as exc:
        manifests.load("nope")
    assert "blackwhite" in str(exc.value)


# ---------------------------------------------------------------------------
# normalization
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("MOVE_GRASS_WHISTLE", "grass-whistle"),
    ("GrassWhistle", "grass-whistle"),
    ("Grass Whistle", "grass-whistle"),
    ("ITEM_ORAN_BERRY", "oran-berry"),
    ("TRAINER_CLASS_ACE_TRAINER", "ace-trainer"),
    ("", ""),
])
def test_to_slug_reconciles_source_spellings(raw, expected):
    assert normalize.to_slug(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("NidoranM", "nidoran-m"),
    ("NidoranF", "nidoran-f"),
    ("SPECIES_MR_MIME", "mr-mime"),
    ("Ho-Oh", "ho-oh"),
    ("Porygon-Z", "porygon-z"),
    ("Swoobat", "swoobat"),
])
def test_species_slug_handles_irregular_names(raw, expected):
    assert normalize.species_slug(raw) == expected


def test_split_list_drops_none_sentinels():
    assert normalize.split_list("ITEM_ORAN_BERRY,ITEM_NONE,ITEM_SITRUS_BERRY") == [
        "ITEM_ORAN_BERRY", "ITEM_SITRUS_BERRY",
    ]
    assert normalize.split_list("") == []


def test_fix_mojibake_repairs_cp1252_decoded_utf8():
    # Repairs the encoding only -- the apostrophe is genuinely typographic.
    assert normalize.fix_mojibake("Cilanâ€™s Team") == "Cilan’s Team"
    assert normalize.fix_mojibake("Cheren's Team") == "Cheren's Team"


def test_clean_text_repairs_then_folds_to_ascii():
    assert normalize.clean_text("Cilanâ€™s Team") == "Cilan's Team"
    assert normalize.clean_text("Pokémon — Route 1") == "Pokémon - Route 1"


def test_title_key_collapses_whitespace():
    assert normalize.title_key("  Striaton   City  Gym ") == "striaton city gym"


# ---------------------------------------------------------------------------
# preview validation
# ---------------------------------------------------------------------------

def test_preview_validators_reject_bad_data():
    rows = [{"a": "1", "vg": "11"}, {"a": "1", "vg": "14"}]
    with pytest.raises(preview.PreviewError):
        preview.expect_row_count(rows, 3, "test")
    with pytest.raises(preview.PreviewError):
        preview.expect_column_value(rows, "vg", 11, "test")
    with pytest.raises(preview.PreviewError):
        preview.expect_unique(rows, "a", "test")
    with pytest.raises(preview.PreviewError):
        preview.expect_column_in(rows, "vg", ["11"], "test")
    with pytest.raises(preview.PreviewError):
        preview.expect_references(rows, "a", {"2"}, "test", "things")


def test_schema_subset_keeps_only_available_columns():
    columns = schemas.subset(schemas.TRAINER_POKEMON_COLUMNS, ["encounter_name", "lvl", "slot"])
    assert schemas.names(columns) == ["encounter_name", "lvl", "slot"]


# ---------------------------------------------------------------------------
# generated SQL
# ---------------------------------------------------------------------------

def _simple_load():
    return GuardedLoad(
        title="test",
        stages=[StageTable("thing_stage", [("a", "text"), ("b", "integer")], [{"a": "x", "b": 1}])],
        guards=[Guard("(SELECT count(*) FROM thing_stage) <> 1", "Bad count")],
        statements=["INSERT INTO thing (a, b) SELECT a, b FROM thing_stage"],
        metrics=[Metric("thing_rows", "SELECT count(*) FROM thing")],
    )


def test_dry_run_rolls_back_and_apply_commits():
    load = _simple_load()
    paths = {"thing_stage": "/tmp/thing_stage.csv"}

    dry = load.build_sql(paths, rollback=True)
    assert dry.rstrip().endswith("ROLLBACK;")
    assert "COMMIT;" not in dry

    live = load.build_sql(paths, rollback=False)
    assert live.rstrip().endswith("COMMIT;")
    assert "ROLLBACK;" not in live


def test_generated_sql_stages_guards_and_reports():
    sql = _simple_load().build_sql({"thing_stage": "/tmp/thing_stage.csv"}, rollback=True)
    assert "CREATE TEMP TABLE thing_stage" in sql
    assert "ON COMMIT DROP" in sql
    assert "\\copy thing_stage FROM '/tmp/thing_stage.csv'" in sql
    assert "RAISE EXCEPTION 'Bad count'" in sql
    assert "SELECT 'thing_rows' AS metric" in sql


def test_guard_messages_escape_quotes():
    load = GuardedLoad(
        title="t",
        stages=[StageTable("s", [("a", "text")], [{"a": "1"}])],
        guards=[Guard("true", "Trainer's data is already loaded")],
    )
    sql = load.build_sql({"s": "/tmp/s.csv"}, rollback=True)
    assert "RAISE EXCEPTION 'Trainer''s data is already loaded'" in sql


# ---------------------------------------------------------------------------
# pipeline wiring
# ---------------------------------------------------------------------------

class _Args:
    def __init__(self, manifest):
        self.manifest = manifest
        self.preview_dir = None
        self.apply = False


def test_trainers_pipeline_guards_against_double_load():
    sql = gen5_trainers.build_load(_Args("blackwhite")).build_sql(
        {"trainer_pool_stage": "/tmp/a.csv", "trainer_pokemon_stage": "/tmp/b.csv"},
        rollback=True,
    )
    assert "version_group_id = 11 AND load_build = 6" in sql
    assert "already loaded" in sql
    # Party rows must be linked and the load must abort if any are not.
    assert "SET trainer_id = tp.trainer_id" in sql
    assert "missing trainer_id links" in sql


def test_event_boss_pipeline_binds_trainers_portably():
    sql = gen5_event_bosses.build_load(_Args("blackwhite")).build_sql(
        {"event_boss_stage": "/tmp/c.csv"}, rollback=True
    )
    # Resolution is by encounter_name, never by the preview's baked-in
    # trainer_id, which is only valid in the database it came from.
    assert "tp.encounter_name = s.encounter_name" in sql
    assert "resolved_trainer_id" in sql
    assert "does not resolve to exactly one" in sql
