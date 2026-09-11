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

  // --- 3. battle handoff: pre-select the leads and render the party bar ---
  try {
    var rawBattle = localStorage.getItem('lockleyBattle');
    if (!rawBattle) return;
    var battle = JSON.parse(rawBattle);
    if (!battle || !window.jQuery) return;
    var playerTeam = battle.playerSets || [];
    var opponentTeam = battle.opponentSets || [];

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
        refreshHighlights();
      }

      function refreshHighlights() {
        var values = [];
        try {
          values = [selectors.eq(0).val(), selectors.eq(1).val()];
        } catch (e) { return; }
        var buttons = document.querySelectorAll('.lockley-party-mon');
        for (var i = 0; i < buttons.length; i++) {
          var btn = buttons[i];
          var side = Number(btn.getAttribute('data-side'));
          var active = btn.getAttribute('data-set') === values[side];
          btn.style.borderColor = active ? (side === 0 ? '#7ec8e3' : '#f2b46b') : 'transparent';
          btn.style.background = active ? 'rgba(255,255,255,0.08)' : 'transparent';
        }
      }

      // The party bar: both teams as clickable sprites, hzla-style, above
      // the calculator. Clicking a mon loads its set into that side's panel.
      try {
        var bar = document.createElement('div');
        bar.id = 'lockley-party-bar';
        bar.style.cssText = 'display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px 24px;' +
          'padding:8px 14px;background:#20262c;color:#dfe7ee;font:12px/1.3 sans-serif;' +
          'border-bottom:2px solid #39434c;';

        function makeGroup(title, team, side, accent) {
          var group = document.createElement('div');
          group.style.cssText = 'display:flex;align-items:center;gap:4px;flex-wrap:wrap;';
          var caption = document.createElement('span');
          caption.textContent = title;
          caption.style.cssText = 'font-weight:bold;margin-right:6px;color:' + accent + ';';
          group.appendChild(caption);
          team.forEach(function (mon) {
            if (!mon || !mon.id) return;
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'lockley-party-mon';
            btn.setAttribute('data-side', String(side));
            btn.setAttribute('data-set', mon.id);
            btn.title = mon.id;
            btn.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:0;' +
              'border:2px solid transparent;border-radius:8px;background:transparent;' +
              'cursor:pointer;padding:2px 4px;color:inherit;font:inherit;';
            if (mon.sprite) {
              var img = document.createElement('img');
              img.src = mon.sprite;
              img.width = 40; img.height = 40;
              img.style.cssText = 'image-rendering:pixelated;object-fit:contain;';
              img.onerror = function () { this.style.display = 'none'; };
              btn.appendChild(img);
            }
            var name = document.createElement('span');
            name.textContent = mon.label || mon.id;
            name.style.cssText = 'font-size:10px;max-width:64px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
            btn.appendChild(name);
            btn.onclick = function () { pick(side, mon.id); };
            group.appendChild(btn);
          });
          return group;
        }

        bar.appendChild(makeGroup('Your team', playerTeam, 0, '#7ec8e3'));
        bar.appendChild(makeGroup((battle.trainerName || 'Trainer'), opponentTeam, 1, '#f2b46b'));
        document.body.insertBefore(bar, document.body.firstChild);
        // A dropdown pick should move the highlight too.
        $(document).on('change', 'input.set-selector', refreshHighlights);
      } catch (e) { /* the bar is optional */ }

      pick(0, playerTeam[0] && playerTeam[0].id);
      pick(1, opponentTeam[0] && opponentTeam[0].id);
    }, 250);
  } catch (e) { /* no handoff */ }
})();
