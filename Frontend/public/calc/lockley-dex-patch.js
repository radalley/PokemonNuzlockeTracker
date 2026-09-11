// Lockley addition — the one file in this directory that is not part of
// the Smogon mirror (see LOCKLEY-README.md). Applies the active game's
// dex modifications (a ROM hack's changed base stats, types, abilities,
// and move data) before the calculator initializes. Lockley writes
// localStorage.lockleyDexPatch alongside customsets when opening the
// calc; a vanilla game clears it, so stock data stands. Best-effort by
// design: any failure leaves the calculator exactly as Smogon shipped it.
(function () {
  try {
    var raw = localStorage.getItem('lockleyDexPatch');
    if (!raw || !window.calc) return;
    var patch = JSON.parse(raw);
    var gen = Number(patch && patch.generation);
    if (!gen) return;

    var speciesDex = (calc.SPECIES || [])[gen] || {};
    Object.keys(patch.species || {}).forEach(function (name) {
      var target = speciesDex[name];
      var p = patch.species[name];
      if (!target || !p) return;
      if (p.bs) {
        target.bs = target.bs || {};
        Object.keys(p.bs).forEach(function (k) {
          if (p.bs[k] != null) target.bs[k] = p.bs[k];
        });
      }
      if (p.types && p.types.length) target.types = p.types.slice();
      if (p.ability) {
        target.abilities = target.abilities || {};
        target.abilities[0] = p.ability;
      }
    });

    var movesDex = (calc.MOVES || [])[gen] || {};
    Object.keys(patch.moves || {}).forEach(function (name) {
      var target = movesDex[name];
      var p = patch.moves[name];
      if (!target || !p) return;
      if (p.bp != null) target.bp = p.bp;
      if (p.type) target.type = p.type;
      if (p.category) target.category = p.category;
    });
  } catch (e) {
    // leave the calculator untouched
  }
})();
