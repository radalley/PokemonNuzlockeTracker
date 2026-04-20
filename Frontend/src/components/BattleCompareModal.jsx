import { useState } from 'react'
import Sprite from './Sprite'
import { TypeIconRow } from './TypeIcon'
import PokemonStatRows from './PokemonStatRows'

function formatType(t) {
  if (!t) return null
  return t.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase())
}

function formatAbility(a) {
  if (!a) return null
  return a.replace(/^ABILITY_/i, '').replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase())
}

function TypeBadges({ type1, type2 }) {
  const t1 = formatType(type1)
  const t2 = formatType(type2)
  return (
    <TypeIconRow types={[t1, t2]} height={14} gap={3} justifyContent="center" style={{ marginTop: '3px' }} />
  )
}


function BattleCompareModal({
  playerParty = [],
  opponentParty = [],
  trainerName,
  subtitle,
  battleLoading = false,
  defeated = false,
  battleSaving = false,
  battleResult = null,
  onClose,
  onMarkVictory,
}) {
  const [selectedPlayer, setSelectedPlayer] = useState(null)
  const [selectedOpponent, setSelectedOpponent] = useState(null)

  const togglePlayer = (idx) => setSelectedPlayer(prev => prev === idx ? null : idx)
  const toggleOpponent = (idx) => setSelectedOpponent(prev => prev === idx ? null : idx)

  const playerMon = selectedPlayer != null ? playerParty[selectedPlayer] : null
  const opponentMon = selectedOpponent != null ? opponentParty[selectedOpponent] : null
  const hasPlayer = playerMon != null
  const hasOpponent = opponentMon != null
  const hasBoth = hasPlayer && hasOpponent
  const hasOne = hasPlayer || hasOpponent

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0,
        backgroundColor: 'rgba(0,0,0,0.75)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 2000, cursor: 'default',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: 'min(1200px, 95vw)', maxHeight: '88vh', overflowY: 'auto',
          background: '#1b1c23', border: '1px solid #3a3c47', borderRadius: '10px',
          padding: '18px 18px 14px', display: 'flex', flexDirection: 'column', gap: '0',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <div style={{ fontSize: '1.05em', fontWeight: 'bold' }}>Battle: {trainerName}</div>
          <div style={{ fontSize: '0.8em', color: '#999' }}>{subtitle}</div>
        </div>

        {/* Three columns */}
        <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr 200px', gap: '12px', flex: 1 }}>

          {/* Left — Player party */}
          <div style={{ border: '1px solid #343746', borderRadius: '8px', padding: '10px' }}>
            <div style={{ fontWeight: 'bold', marginBottom: '8px', fontSize: '0.88em', color: '#ccc' }}>Your Party</div>
            {battleLoading ? (
              <div style={{ color: '#999', fontSize: '0.82em' }}>Loading...</div>
            ) : playerParty.length === 0 ? (
              <div style={{ color: '#999', fontSize: '0.82em' }}>No party Pokémon.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                {playerParty.map((mon, idx) => (
                  <div
                    key={mon.pokemon_id}
                    onClick={() => togglePlayer(idx)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '7px',
                      border: `1px solid ${selectedPlayer === idx ? '#7ec8e3' : '#2e2f3a'}`,
                      borderRadius: '6px', padding: '5px 6px', cursor: 'pointer',
                      background: selectedPlayer === idx ? 'rgba(126,200,227,0.08)' : 'transparent',
                      transition: 'border-color 0.1s',
                    }}
                  >
                    <Sprite speciesId={mon.species_id} size={34} shiny={mon.shiny === 'True' || mon.shiny === true} />
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: '0.8em', fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {mon.nickname || mon.species_name}
                      </div>
                      <div style={{ fontSize: '0.68em', color: '#a0a2ad', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {mon.species_name}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Center — Stats / Comparison */}
          <div style={{ border: '1px solid #343746', borderRadius: '8px', padding: '14px' }}>
            {!hasOne ? (
              <div style={{ height: '100%', minHeight: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#444', fontSize: '0.82em', textAlign: 'center' }}>
                Select a Pokémon from either party to view stats
              </div>
            ) : hasBoth ? (
              <div>
                {/* Sprites + names */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '14px' }}>
                  <div style={{ textAlign: 'center', flex: 1 }}>
                    <Sprite speciesId={playerMon.species_id} size={56} shiny={playerMon.shiny === 'True' || playerMon.shiny === true} />
                    <div style={{ fontSize: '0.8em', fontWeight: 'bold', marginTop: '2px' }}>{playerMon.nickname || playerMon.species_name}</div>
                    <div style={{ fontSize: '0.7em', color: '#aaa' }}>{playerMon.species_name}</div>
                    <TypeBadges type1={playerMon.type1} type2={playerMon.type2} />
                  </div>
                  <div style={{ fontSize: '0.78em', color: '#555', padding: '0 10px', paddingBottom: '22px' }}>vs</div>
                  <div style={{ textAlign: 'center', flex: 1 }}>
                    <Sprite speciesId={opponentMon.species_id} size={56} />
                    <div style={{ fontSize: '0.8em', fontWeight: 'bold', marginTop: '2px' }}>{opponentMon.species_name}</div>
                    <div style={{ fontSize: '0.7em', color: '#aaa' }}>Lvl {opponentMon.lvl}</div>
                    <TypeBadges type1={opponentMon.type1} type2={opponentMon.type2} />
                  </div>
                </div>
                <div style={{ display: 'grid', gap: '10px', alignItems: 'start' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 44px 92px 44px minmax(0, 1fr)', columnGap: '8px', alignItems: 'center', paddingBottom: '6px', marginBottom: '2px', borderBottom: '1px solid #2e2f3a', fontSize: '0.78em' }}>
                    <span />
                    <span style={{ color: '#ddd', textAlign: 'right' }}>{playerMon.bst ?? '—'}</span>
                    <span style={{ color: '#888', textAlign: 'center' }}>BST</span>
                    <span style={{ color: '#ddd', textAlign: 'left' }}>{opponentMon.bst ?? '—'}</span>
                    <span />
                  </div>
                  <PokemonStatRows
                    stats={playerMon}
                    compareStats={opponentMon}
                    nature={playerMon.nature || ''}
                    rowGap="7px"
                    columnGap="10px"
                    labelColumnWidth={55}
                    valueColumnWidth={35}
                    barHeight={8}
                    labelFontSize="0.72em"
                    valueFontSize="0.78em"
                    trackColor="#2a2b33"
                  />
                </div>
              </div>
            ) : (
              /* Single pokemon view */
              (() => {
                const mon = hasPlayer ? playerMon : opponentMon
                const isPlayer = hasPlayer
                return (
                  <div>
                    <div style={{ textAlign: 'center', marginBottom: '12px' }}>
                      <Sprite speciesId={mon.species_id} size={68} shiny={isPlayer && (mon.shiny === 'True' || mon.shiny === true)} />
                      <div style={{ fontSize: '0.88em', fontWeight: 'bold', marginTop: '4px' }}>
                        {isPlayer ? (mon.nickname || mon.species_name) : mon.species_name}
                      </div>
                      <div style={{ fontSize: '0.74em', color: '#aaa' }}>
                        {isPlayer ? mon.species_name : `Lvl ${mon.lvl}`}
                      </div>
                      <TypeBadges type1={mon.type1} type2={mon.type2} />
                      {formatAbility(mon.ability1) && (
                        <div style={{ fontSize: '0.72em', color: '#d9deea', marginTop: '5px' }}>{formatAbility(mon.ability1)}</div>
                      )}
                      <div style={{ fontSize: '0.72em', color: '#aaa', marginTop: '5px' }}>
                        BST {mon.bst ?? '—'}{isPlayer && mon.nature ? ` • ${mon.nature}` : ''}
                      </div>
                    </div>
                    <PokemonStatRows
                      stats={mon}
                      nature={isPlayer ? (mon.nature || '') : ''}
                      rowGap="5px"
                      labelColumnWidth={104}
                      labelTextWidth={28}
                      modifierWidth={38}
                      valueColumnWidth={30}
                      barHeight={6}
                      labelFontSize="0.7em"
                      valueFontSize="0.74em"
                      trackColor="#2a2b33"
                    />
                  </div>
                )
              })()
            )}
          </div>

          {/* Right — Opponent party */}
          <div style={{ border: '1px solid #343746', borderRadius: '8px', padding: '10px' }}>
            <div style={{ fontWeight: 'bold', marginBottom: '8px', fontSize: '0.88em', color: '#ccc' }}>Opponent Team</div>
            {opponentParty.length === 0 ? (
              <div style={{ color: '#999', fontSize: '0.82em' }}>No party data.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                {opponentParty.map((mon, idx) => (
                  <div
                    key={`${mon.species_id}-${idx}`}
                    onClick={() => toggleOpponent(idx)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '7px',
                      border: `1px solid ${selectedOpponent === idx ? '#f2b46b' : '#2e2f3a'}`,
                      borderRadius: '6px', padding: '5px 6px', cursor: 'pointer',
                      background: selectedOpponent === idx ? 'rgba(242,180,107,0.08)' : 'transparent',
                      transition: 'border-color 0.1s',
                    }}
                  >
                    <Sprite speciesId={mon.species_id} size={34} />
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: '0.8em', fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {mon.species_name}
                      </div>
                      <div style={{ fontSize: '0.68em', color: '#a0a2ad' }}>Lvl {mon.lvl}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Battle result banners */}
        {battleResult?.success && (
          <div style={{ marginTop: '12px', border: '1px solid #2d5a2d', background: 'rgba(91,168,91,0.1)', borderRadius: '8px', padding: '10px', textAlign: 'center' }}>
            <div style={{ fontSize: '0.9em', color: '#5ba85b', fontWeight: 'bold' }}>✓ Victory recorded!</div>
          </div>
        )}
        {battleResult?.badge_awarded && (
          <div style={{ marginTop: '12px', border: '1px solid #4a3f21', background: 'rgba(242,180,107,0.08)', borderRadius: '8px', padding: '8px 10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <img src={`/sprites/Badges/${battleResult.badge_awarded.badge_id}.png`} width={28} height={28} alt={battleResult.badge_awarded.badge_name} style={{ imageRendering: 'pixelated' }} />
            <div style={{ fontSize: '0.86em' }}>Badge awarded: <strong>{battleResult.badge_awarded.badge_name}</strong></div>
          </div>
        )}
        {battleResult?.is_gym_leader && !battleResult?.badge_awarded && (
          <div style={{ marginTop: '10px', fontSize: '0.82em', color: '#d0a56c' }}>
            Gym leader win recorded, but no badge assignment was applied.
          </div>
        )}

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '14px' }}>
          <button onClick={onClose} style={{ padding: '6px 12px', cursor: 'pointer' }}>Back</button>
          <button
            onClick={onMarkVictory}
            disabled={defeated || battleSaving || battleLoading || battleResult?.success}
            style={{
              padding: '6px 12px',
              cursor: (defeated || battleResult?.success) ? 'not-allowed' : 'pointer',
              color: (defeated || battleResult?.success) ? '#555' : '#5ba85b',
              borderColor: (defeated || battleResult?.success) ? '#555' : '#5ba85b',
              opacity: (defeated || battleResult?.success) ? 0.6 : 1,
            }}
          >
            {defeated || battleResult?.success ? '✓ Victory' : battleSaving ? 'Saving...' : 'Mark Victory'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default BattleCompareModal
