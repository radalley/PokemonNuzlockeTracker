# Vendored: Pokemon Showdown Damage Calculator

This directory is a verbatim mirror of https://calc.pokemonshowdown.com
(the official Smogon damage calculator, MIT license,
https://github.com/smogon/damage-calc), fetched 2026-09-11. No file is
modified.

Lockley serves it same-origin at /calc/ so the battle modal's Calc
button can hand it both teams before opening it: the calculator merges
`localStorage.customsets` into its set index on every page load (its
own Import feature persists through the same key), and same-origin
pages may write that key. Cross-origin seeding of the real
calc.pokemonshowdown.com is impossible (localStorage is origin-scoped
and the site reads only `?gen=` from the URL), which is why the copy
exists.

To refresh the mirror, re-run the fetch against the live site and
replace this directory wholesale; never hand-edit files here.
