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

  // Lockley skin: strip the surrounding chrome, restyle to Lockley's
  // palette. Loaded first so the page never flashes the stock look.
  try {
    var skin = document.createElement('link');
    skin.rel = 'stylesheet';
    skin.href = './lockley-calc.css?4';
    (document.head || document.documentElement).appendChild(skin);
    document.title = 'Lockley Damage Calc';
  } catch (e) { /* stock look stands */ }

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

      // The party strips: each team as clickable sprites directly under
      // its side's Pokemon panel. Clicking a mon loads its set there.
      try {
        function makeStrip(title, team, side, accent) {
          var strip = document.createElement('div');
          strip.className = 'lockley-party-strip';
          var caption = document.createElement('span');
          caption.className = 'lockley-caption';
          caption.textContent = title;
          caption.style.color = accent;
          strip.appendChild(caption);
          team.forEach(function (mon) {
            if (!mon || !mon.id) return;
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'lockley-party-mon';
            btn.setAttribute('data-side', String(side));
            btn.setAttribute('data-set', mon.id);
            btn.title = mon.id;
            if (mon.sprite) {
              var img = document.createElement('img');
              img.src = mon.sprite;
              img.onerror = function () { this.style.display = 'none'; };
              btn.appendChild(img);
            }
            var name = document.createElement('span');
            name.textContent = mon.label || mon.id;
            btn.appendChild(name);
            btn.onclick = function () { pick(side, mon.id); };
            strip.appendChild(btn);
          });
          return strip;
        }

        // The strip lives INSIDE the fieldset with an explicit pixel width
        // measured before insertion. Everything here is shrink-to-fit
        // floats sized to the pixel: a sibling beside the floated fieldset
        // accumulates horizontally in intrinsic sizing, and auto or
        // percentage widths feed back into the float's own width — an
        // explicit width no wider than the existing content is the only
        // thing that leaves the three-column layout untouched.
        function attachStrip(fieldset, strip) {
          if (!fieldset) return;
          var cs = getComputedStyle(fieldset);
          var w = fieldset.clientWidth - parseFloat(cs.paddingLeft || '0') - parseFloat(cs.paddingRight || '0');
          if (w > 40) strip.style.width = Math.floor(w) + 'px';
          fieldset.appendChild(strip);
        }
        attachStrip(document.getElementById('p1'), makeStrip('Your team', playerTeam, 0, '#7ec8e3'));
        attachStrip(document.getElementById('p2'), makeStrip((battle.trainerName || 'Trainer'), opponentTeam, 1, '#f2b46b'));
        // A dropdown pick should move the highlight too.
        $(document).on('change', 'input.set-selector', refreshHighlights);
      } catch (e) { /* the strips are optional */ }

      // Game header: the run's title art plus the battle being planned,
      // replacing the stock text title (hidden by lockley-calc.css).
      try {
        var wrapper = document.querySelector('.wrapper');
        if (wrapper) {
          var head = document.createElement('div');
          head.className = 'lockley-calc-header';
          if (battle.gameLogo) {
            var logo = document.createElement('img');
            logo.src = battle.gameLogo;
            logo.alt = battle.gameName || '';
            logo.className = 'lockley-calc-header-logo';
            logo.onerror = function () { this.style.display = 'none'; };
            head.appendChild(logo);
          }
          var headText = document.createElement('div');
          var line1 = document.createElement('div');
          line1.className = 'lockley-calc-header-title';
          line1.textContent = 'Damage Calculator';
          headText.appendChild(line1);
          var line2 = document.createElement('div');
          line2.className = 'lockley-calc-header-battle';
          line2.textContent = 'Battling ' + (battle.trainerName || 'a trainer') +
            (battle.context ? ' — ' + battle.context : '');
          headText.appendChild(line2);
          head.appendChild(headText);
          wrapper.insertBefore(head, wrapper.firstChild);
          document.body.classList.add('lockley-has-header');
        }
      } catch (e) { /* the stock title stands */ }

      // Fork credit: keep the original creators' credits, framed as what
      // this page is — Lockley's fork of their calculator.
      try {
        var credits = document.querySelector('.credits');
        if (credits) {
          var note = document.createElement('div');
          note.className = 'lockley-credits-note';
          note.textContent = 'Lockley Damage Calc — a fork of the Pokémon Showdown Damage Calculator. All calculator credit to its creators:';
          credits.insertBefore(note, credits.firstChild);
        }
      } catch (e) { /* credits stand as shipped */ }

      // Moveset save: moves picked in a panel showing one of YOUR mons
      // persist onto that mon's stored set, so switching away and back
      // (or reopening the calc from a later battle) keeps them.
      try {
        var playerIds = {};
        playerTeam.forEach(function (mon) { if (mon && mon.id) playerIds[mon.id] = true; });
        $(document).on('change', '.poke-info select.move-selector', function () {
          try {
            var panel = this.closest('.poke-info');
            if (!panel) return;
            var fullname = $(panel).find('input.set-selector').val() || '';
            if (!playerIds[fullname]) return;
            var species = fullname.substring(0, fullname.indexOf(' ('));
            var setName = fullname.substring(fullname.indexOf('(') + 1, fullname.lastIndexOf(')'));
            var moves = [];
            $(panel).find('select.move-selector').each(function () {
              var value = $(this).val();
              if (value && value !== '(No Move)') moves.push(value);
            });
            var stored = JSON.parse(localStorage.getItem('customsets') || '{}') || {};
            if (stored[species] && stored[species][setName]) {
              stored[species][setName].moves = moves;
              localStorage.setItem('customsets', JSON.stringify(stored));
            }
            if (window.setdex && setdex[species] && setdex[species][setName]) {
              setdex[species][setName].moves = moves;
            }
          } catch (e) { /* this pick just won't persist */ }
        });
      } catch (e) { /* saving is optional */ }

      pick(0, playerTeam[0] && playerTeam[0].id);
      pick(1, opponentTeam[0] && opponentTeam[0].id);
    }, 250);
  } catch (e) { /* no handoff */ }
})();
