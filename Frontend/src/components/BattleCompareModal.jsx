import { useState } from 'react'
import BattleFormatPill from './BattleFormatPill'
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

const MODAL_ACTION_BUTTON_STYLE = {
  minHeight: '34px',
  padding: '6px 12px',
  border: '1px solid var(--border-strong)',
  borderRadius: '999px',
  background: 'var(--surface-deep)',
  color: 'var(--text-secondary)',
  cursor: 'pointer',
  font: 'inherit',
  fontSize: '0.82em',
}

const PARTY_SELECT_BUTTON_STYLE = {
  width: '100%',
  display: 'flex',
  alignItems: 'center',
  gap: '7px',
  border: '1px solid var(--border-strong)',
  borderRadius: '999px',
  padding: '5px 8px',
  background: 'var(--surface-deep)',
  color: 'var(--text-primary)',
  cursor: 'pointer',
  font: 'inherit',
  textAlign: 'left',
  transition: 'border-color 0.1s, background-color 0.1s',
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
  onDeclareDefeat = null,
  defeatSaving = false,
  defeatError = '',
  battleType = null,
}) {
  const [selectedPlayer, setSelectedPlayer] = useState(null)
  const [selectedOpponent, setSelectedOpponent] = useState(null)
  const [confirmingDefeat, setConfirmingDefeat] = useState(false)

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
      className="battle-compare__backdrop"
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0,
        backgroundColor: 'rgba(0,0,0,0.75)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 2000, cursor: 'default',
      }}
    >
      <div
        className="battle-compare"
        onClick={e => e.stopPropagation()}
        style={{
          width: 'min(1200px, 95vw)', maxHeight: '88vh', overflowY: 'auto',
          background: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: '10px',
          padding: '18px 18px 14px', display: 'flex', flexDirection: 'column', gap: '0',
        }}
      >
        {/* Header */}
        <div className="battle-compare__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
            <div style={{ fontSize: '1.05em', fontWeight: 'bold' }}>Battle: {trainerName}</div>
            <BattleFormatPill format={battleType} fontSize="0.72em" />
          </div>
          <div style={{ fontSize: '0.8em', color: 'var(--text-secondary)' }}>{subtitle}</div>
        </div>

        {/* Three columns */}
        <div className="battle-compare__grid" style={{ display: 'grid', gridTemplateColumns: '200px 1fr 200px', gap: '12px', flex: 1 }}>

          {/* Left — Player party */}
          <div className="battle-compare__party battle-compare__player" style={{ border: '1px solid var(--border-strong)', borderRadius: '8px', padding: '10px' }}>
            <div style={{ fontWeight: 'bold', marginBottom: '8px', fontSize: '0.88em', color: 'var(--text-primary)' }}>Your Party</div>
            {battleLoading ? (
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.82em' }}>Loading...</div>
            ) : playerParty.length === 0 ? (
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.82em' }}>No party Pokémon.</div>
            ) : (
              <div className="battle-compare__party-list" style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                {playerParty.map((mon, idx) => (
                  <button
                    type="button"
                    key={mon.pokemon_id}
                    onClick={() => togglePlayer(idx)}
                    style={{
                      ...PARTY_SELECT_BUTTON_STYLE,
                      borderColor: selectedPlayer === idx ? '#7ec8e3' : 'var(--border-strong)',
                      background: selectedPlayer === idx ? 'rgba(126,200,227,0.08)' : 'var(--surface-deep)',
                    }}
                  >
                    <Sprite speciesId={mon.species_id} size={34} shiny={mon.shiny === 'True' || mon.shiny === true} />
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: '0.8em', fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {mon.nickname || mon.species_name}
                      </div>
                      <div style={{ fontSize: '0.68em', color: 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {mon.species_name}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Center — Stats / Comparison */}
          <div className="battle-compare__comparison" style={{ border: '1px solid var(--border-strong)', borderRadius: '8px', padding: '14px' }}>
            {!hasOne ? (
              <div style={{ height: '100%', minHeight: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontSize: '0.82em', textAlign: 'center' }}>
                Select a Pokémon from either party to view stats
              </div>
            ) : hasBoth ? (
              <div>
                {/* Sprites + names */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '14px' }}>
                  <div style={{ textAlign: 'center', flex: 1 }}>
                    <Sprite speciesId={playerMon.species_id} size={56} shiny={playerMon.shiny === 'True' || playerMon.shiny === true} />
                    <div style={{ fontSize: '0.8em', fontWeight: 'bold', marginTop: '2px' }}>{playerMon.nickname || playerMon.species_name}</div>
                    <div style={{ fontSize: '0.7em', color: 'var(--text-secondary)' }}>{playerMon.species_name}</div>
                    <TypeBadges type1={playerMon.type1} type2={playerMon.type2} />
                  </div>
                  <div style={{ fontSize: '0.78em', color: 'var(--text-secondary)', padding: '0 10px', paddingBottom: '22px' }}>vs</div>
                  <div style={{ textAlign: 'center', flex: 1 }}>
                    <Sprite speciesId={opponentMon.species_id} size={56} />
                    <div style={{ fontSize: '0.8em', fontWeight: 'bold', marginTop: '2px' }}>{opponentMon.species_name}</div>
                    <div style={{ fontSize: '0.7em', color: 'var(--text-secondary)' }}>Lvl {opponentMon.lvl}</div>
                    <TypeBadges type1={opponentMon.type1} type2={opponentMon.type2} />
                  </div>
                </div>
                <div style={{ display: 'grid', gap: '10px', alignItems: 'start' }}>
                  <div className="battle-compare__bst-row" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 44px 92px 44px minmax(0, 1fr)', columnGap: '8px', alignItems: 'center', paddingBottom: '6px', marginBottom: '2px', borderBottom: '1px solid var(--border)', fontSize: '0.78em' }}>
                    <span />
                    <span style={{ color: 'var(--text-primary)', textAlign: 'right' }}>{playerMon.bst ?? '—'}</span>
                    <span style={{ color: 'var(--text-secondary)', textAlign: 'center' }}>BST</span>
                    <span style={{ color: 'var(--text-primary)', textAlign: 'left' }}>{opponentMon.bst ?? '—'}</span>
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
                    trackColor="var(--surface-deep)"
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
                      <div style={{ fontSize: '0.74em', color: 'var(--text-secondary)' }}>
                        {isPlayer ? mon.species_name : `Lvl ${mon.lvl}`}
                      </div>
                      <TypeBadges type1={mon.type1} type2={mon.type2} />
                      {formatAbility(mon.ability1) && (
                        <div style={{ fontSize: '0.72em', color: 'var(--text-primary)', marginTop: '5px' }}>{formatAbility(mon.ability1)}</div>
                      )}
                      <div style={{ fontSize: '0.72em', color: 'var(--text-secondary)', marginTop: '5px' }}>
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
                      trackColor="var(--surface-deep)"
                    />
                  </div>
                )
              })()
            )}
          </div>

          {/* Right — Opponent party */}
          <div className="battle-compare__party battle-compare__opponent" style={{ border: '1px solid var(--border-strong)', borderRadius: '8px', padding: '10px' }}>
            <div style={{ fontWeight: 'bold', marginBottom: '8px', fontSize: '0.88em', color: 'var(--text-primary)' }}>Opponent Team</div>
            {opponentParty.length === 0 ? (
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.82em' }}>No party data.</div>
            ) : (
              <div className="battle-compare__party-list" style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                {opponentParty.map((mon, idx) => (
                  <button
                    type="button"
                    key={`${mon.species_id}-${idx}`}
                    onClick={() => toggleOpponent(idx)}
                    style={{
                      ...PARTY_SELECT_BUTTON_STYLE,
                      borderColor: selectedOpponent === idx ? '#f2b46b' : 'var(--border-strong)',
                      background: selectedOpponent === idx ? 'rgba(242,180,107,0.08)' : 'var(--surface-deep)',
                    }}
                  >
                    <Sprite speciesId={mon.species_id} size={34} />
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: '0.8em', fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {mon.species_name}
                      </div>
                      <div style={{ fontSize: '0.68em', color: 'var(--text-secondary)' }}>Lvl {mon.lvl}</div>
                    </div>
                  </button>
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

        {defeatError && (
          <div style={{ marginTop: '10px', fontSize: '0.8em', color: '#e05252', textAlign: 'right' }}>{defeatError}</div>
        )}

        {/* Footer */}
        <div className="battle-compare__footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', marginTop: '14px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {onDeclareDefeat && !battleResult?.success && (
              confirmingDefeat ? (
                <>
                  <span style={{ fontSize: '0.78em', color: '#e05252' }}>
                    End this attempt? {trainerName} is recorded as the killer.
                  </span>
                  <button type="button" onClick={() => setConfirmingDefeat(false)} disabled={defeatSaving} style={MODAL_ACTION_BUTTON_STYLE}>
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={onDeclareDefeat}
                    disabled={defeatSaving}
                    style={{ ...MODAL_ACTION_BUTTON_STYLE, borderColor: '#e05252', color: '#e05252', background: 'rgba(224,82,82,0.12)', cursor: defeatSaving ? 'wait' : 'pointer' }}
                  >
                    {defeatSaving ? 'Ending...' : '☠ Confirm Defeat'}
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => setConfirmingDefeat(true)}
                  style={{ ...MODAL_ACTION_BUTTON_STYLE, borderColor: '#5a2d2d', color: '#e05252' }}
                  title="Lost this battle? End the attempt and record the killer."
                >
                  Declare Defeat
                </button>
              )
            )}
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
          <button type="button" onClick={onClose} style={MODAL_ACTION_BUTTON_STYLE}>Back</button>
          <button
            type="button"
            onClick={onMarkVictory}
            disabled={defeated || battleSaving || battleLoading || battleResult?.success}
            style={{
              ...MODAL_ACTION_BUTTON_STYLE,
              background: (defeated || battleResult?.success) ? 'var(--surface-deep)' : 'rgba(91,168,91,0.12)',
              cursor: (defeated || battleResult?.success) ? 'not-allowed' : 'pointer',
              color: (defeated || battleResult?.success) ? 'var(--text-secondary)' : '#5ba85b',
              borderColor: (defeated || battleResult?.success) ? 'var(--border-strong)' : '#5ba85b',
              opacity: (defeated || battleResult?.success) ? 0.6 : 1,
            }}
          >
            {defeated || battleResult?.success ? '✓ Victory' : battleSaving ? 'Saving...' : 'Mark Victory'}
          </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default BattleCompareModal
