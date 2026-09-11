# Vendored: Pokemon Showdown Damage Calculator

This directory is a verbatim mirror of https://calc.pokemonshowdown.com
(the official Smogon damage calculator, MIT license,
https://github.com/smogon/damage-calc), fetched 2026-09-11.

Two deliberate deviations, both Lockley's, nothing else touched:
- `lockley-dex-patch.js` (a new file, the Lockley bridge): applies the
  active game's dex modifications (a ROM hack's changed base stats,
  types, abilities, and move data — `localStorage.lockleyDexPatch`,
  served by `/api/games/<id>/calc-dex-patch`; a vanilla game clears the
  key); canonicalizes imported sets' move names against the dex by id
  ('Mud Slap' -> 'Mud-Slap', unresolvable customs dropped); and, when
  `localStorage.lockleyBattle` names a battle, selects the player's
  lead against the trainer's lead on load and shows a confirmation
  banner.
- `index.html` gains the single script tag loading it (after the data
  files, before the calculator initializes; bump its `?n` query on
  every bridge change so cached copies retire).

Lockley serves it same-origin at /calc/ so the battle modal's Calc
button can hand it both teams before opening it: the calculator merges
`localStorage.customsets` into its set index on every page load (its
own Import feature persists through the same key), and same-origin
pages may write that key. Cross-origin seeding of the real
calc.pokemonshowdown.com is impossible (localStorage is origin-scoped
and the site reads only `?gen=` from the URL), which is why the copy
exists.

To refresh the mirror, re-run the fetch against the live site, replace
this directory wholesale, then re-add the two deviations above; never
hand-edit any other file here.
