# Blaze Black early item seed analysis

Analyzed and implemented locally 2026-09-23. The guarded implementation is
`Backend/migrations/20260923_blazeblack_split_item_sources.sql`; this file
retains the research boundary. Full detail is in
`docs/blaze-black-item-seed-analysis.md`.

- Scope is Blaze Black `game_id=1001` through Burgh. Use Serebii Black/White
  wild-held data against the local Blaze Black encounter tables, and Bulbapedia
  Gen V dust-cloud data.
- Progression corrections: Pinwheel Outside is pre-Lenora; Pinwheel Inside is
  post-Lenora/pre-Burgh; Route 1 dark grass and Wellspring B1F are Surf-gated;
  Surf tables are unavailable; fishing is available because Blaze Black moves
  the Super Rod to Route 3. Thief is on Wellspring Cave 1F.
- Lenora has 44 held-item candidate names. Colbur Berry is not directly
  thiefable from Chingling because the Dark hit consumes it first; excluding
  it leaves 43 ordinary Thief names.
- Wellspring dust clouds add 28 names: 17 gems at 3% per cloud, ten stones at
  0.6% per cloud, Everstone at 3%. Four overlap held items, leaving 67 unique
  Lenora item names across ordinary Thief + dust clouds.
- Pinwheel Inside adds ten Burgh-source names; five genuinely new names are
  Kebia Berry, King's Rock, Mental Herb, Occa Berry, and Rindo Berry.
- Current free-text `method` rows are too flat for this volume. Recommended:
  additive `curated_split_item_sources` children with method kind, species,
  chance, detail, provenance and sort order. UI groups collapsed Thief/Dust
  sections; item rows expand to sources. Store each item at earliest split.
- Implementation gate: decide whether Colbur is omitted or represented as a
  conditional Pickup/Covet source. Seed Blaze Black only; verify Volt White
  separately.
