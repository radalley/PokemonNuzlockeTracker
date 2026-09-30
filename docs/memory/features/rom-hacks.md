# ROM Hacks

ROM hacks are bonus games: their own `games` rows (reserved ids 1000+, own
version group, `is_rom_hack`, `base_game_id`) seeded by cloning the base
game's script and loaded from the hack's own ETL. NewRun lists them in a
ROM Hacks section badged "Hack of <base>"; logos and trainer sprites fall
back to the base game's assets.

Blaze Black / Volt White (games 1001/1002, version group 1001, load build 7)
is the first: parsed from Drayano's 3.1 documentation into 355 trainers
(Regular and Clean abilities both stored, doc-exact boss movesets), 61
bosses matched 1:1 to the vanilla skeleton (starter-conditional rivals,
game-split N finale, post-game replacement fights as Special Battles), and
2,312 wild encounter rows (2,306 from the doc + 6 inherited Starter rows)
including 1% legendary slots, SPECIAL encounters (Zen Darmanitan, Musharna,
Phione, Volcarona), and game exclusives incl. split-game legendaries
(Tornadus->VW/Thundurus->BB roamer, opposite-box dragon at Giant Chasm).
`etl.pipelines.fill_encounter_gaps` runs after `load_encounters` and
inherits base-game pool rows for canonical locations the docs omit
(keyed off games.base_game_id, generic for future hacks). The N's Castle
story capture is skipped loudly: no canonical location, matching vanilla.

Launch state: valid on the LOCAL dev database only. Production launch is a
manual runbook (`docs/blazeblack-launch-runbook.md`): migrations, data
loads, verify hidden, flip `valid_game='valid'`.

The species/learnset override layer (2026-08-25) closed the moveset
fidelity gap: overrides keyed at vg 1001 carry Regular-mode abilities for
all 649 species, 138 changed stat spreads, 18 retypings, 8,794 materialized
level-up learnset rows (vanilla copy + the doc's +/-/= deltas, incl. family
blocks and the Eevee/monkey full restructures), and 46 rebalanced moves.
Read paths (party endpoints, pokebank stats, move resolvers) prefer exact
version-group rows and fall back to the base game; vanilla queries never
see override rows. Load via `load_species_overrides blazeblack --apply`.
Remaining caveat: Drayano's custom move "Wood Horn" (Pinsir/Heracross
learnsets) does not exist in our move data and is skipped with a note.
