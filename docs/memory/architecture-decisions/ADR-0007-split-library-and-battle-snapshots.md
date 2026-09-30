# ADR-0007: Shared split library and immutable battle snapshots

Accepted 2026-09-17; extended with structured item sources 2026-09-23.

- Shared items are exact-game `curated_split_items`, keyed by stable split.
  Admin input remains split, item and method; no collection state is tracked.
- Repeatable/overlapping acquisition methods live in additive
  `curated_split_item_sources` rows with stable key, kind, optional species,
  chance, detail and URL. Manual text is preserved as a manual source.
- Attempt battle history remains immutable ordered JSON in
  `attempt_battle_records`; explicit battle deaths and recorded forms are not
  reconstructed from current Box state.
- Desktop stats and splits live outside the 1126px attempt sheet. Below 1820px
  they become overlay drawers pending the full mobile design.
- Guarded 20260917 and 20260923 migrations own the schema. RLS blocks direct
  clients; Flask owns writes and scoped reads. Production is untouched.
