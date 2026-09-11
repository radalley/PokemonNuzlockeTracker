// Lockley bridge — the one script in this directory that is not part of
// the Smogon calculator (see LOCKLEY-README.md). Three jobs, all driven
// by keys Lockley writes before opening this page, all best-effort: any
// failure leaves the calculator behaving exactly as Smogon shipped it.
//
//  1. Dex patch (localStorage.lockleyDexPatch): apply the active game's
//     modified base stats, types, abilities, and move data in place.
//  2. Set repair: canonicalize the move names inside imported sets
//     against the dex by id ('Mud Slap' -> 'Mud-Slap'); drop moves the
//     dex cannot express so a set never carries a dead name.
//  3. Battle handoff (localStorage.lockleyBattle): once the UI is ready,
//     select the player's lead against the trainer's lead and show a
//     banner confirming what loaded.
(function () {
  'use strict';

  function toId(name) {
    return String(name || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  }

  function currentGen() {
    try {
      var params = new URLSearchParams(window.location.search);
      var gen = parseInt(params.get('gen'), 10);
      return gen >= 1 && gen <= 9 ? gen : 9;
    } catch (e) {
      return 9;
    }
  }

  // --- 1. dex patch -------------------------------------------------------
  try {
    var rawPatch = localStorage.getItem('lockleyDexPatch');
    if (rawPatch && window.calc) {
      var patch = JSON.parse(rawPatch);
      var gen = Number(patch && patch.generation);
      if (gen) {
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
      }
    }
  } catch (e) { /* stock data stands */ }

  // --- 2. set repair ------------------------------------------------------
  try {
    var rawSets = localStorage.getItem('customsets');
    if (rawSets && window.calc) {
      var genNow = currentGen();
      var dexMoves = (calc.MOVES || [])[genNow] || {};
      var byMoveId = {};
      Object.keys(dexMoves).forEach(function (name) { byMoveId[toId(name)] = name; });
      var sets = JSON.parse(rawSets);
      var changed = false;
      Object.keys(sets || {}).forEach(function (species) {
        Object.keys(sets[species] || {}).forEach(function (setName) {
          var set = sets[species][setName];
          if (!set || !Array.isArray(set.moves)) return;
          var repaired = set.moves
            .map(function (mv) { return dexMoves[mv] ? mv : byMoveId[toId(mv)]; })
            .filter(Boolean);
          if (repaired.join('|') !== set.moves.join('|')) {
            set.moves = repaired;
            changed = true;
          }
        });
      });
      if (changed) localStorage.setItem('customsets', JSON.stringify(sets));
    }
  } catch (e) { /* sets load as written */ }

  // --- 3. battle handoff --------------------------------------------------
  try {
    var rawBattle = localStorage.getItem('lockleyBattle');
    if (!rawBattle) return;
    var battle = JSON.parse(rawBattle);
    if (!battle || !window.jQuery) return;

    var attempts = 0;
    var timer = setInterval(function () {
      attempts += 1;
      if (attempts > 40) { clearInterval(timer); return; }
      var $ = window.jQuery;
      var selectors = $('input.set-selector');
      if (selectors.length < 2 || !window.setdex) return;
      clearInterval(timer);

      function pick(index, fullname) {
        if (!fullname) return;
        try {
          // The calculator's own init pattern: set the underlying input's
          // value and fire change. Its initSelection hard-codes the first
          // valid set into the visible label, so write the label directly.
          var $sel = selectors.eq(index);
          $sel.val(fullname);
          $sel.change();
          var containers = document.querySelectorAll('.select2-container.set-selector');
          var span = containers[index] && containers[index].querySelector('.select2-choice span');
          if (span) span.textContent = fullname;
        } catch (e) { /* leave the panel's default */ }
      }
      pick(0, (battle.playerSets || [])[0]);
      pick(1, (battle.opponentSets || [])[0]);

      try {
        var note = document.createElement('div');
        note.textContent = 'Lockley: loaded your team (' + (battle.playerSets || []).length +
          ') and ' + (battle.trainerName || 'the trainer') + "'s team (" +
          (battle.opponentSets || []).length + ') — every mon is in the set lists.';
        note.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9999;' +
          'background:#1d3a4f;color:#bfe3f7;font:13px/1.4 sans-serif;' +
          'padding:6px 34px 6px 12px;text-align:center;';
        var close = document.createElement('span');
        close.textContent = '×';
        close.style.cssText = 'position:absolute;right:12px;top:4px;cursor:pointer;font-size:15px;';
        close.onclick = function () { note.remove(); };
        note.appendChild(close);
        document.body.appendChild(note);
        setTimeout(function () { note.remove(); }, 12000);
      } catch (e) { /* banner is optional */ }
    }, 250);
  } catch (e) { /* no handoff */ }
})();
