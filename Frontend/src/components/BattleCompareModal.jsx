import { useEffect, useRef, useState } from 'react'
import BattleFormatPill from './BattleFormatPill'
import Sprite from './Sprite'
import { Button } from './Button'
import TypeIcon, { TypeIconRow } from './TypeIcon'
import PokemonStatRows from './PokemonStatRows'
import { getDamageCalc, openCalcWithTeams, prefetchDexPatch } from '../utils/damageCalc'
import { battleMoveSlots, hasEstimatedMoves } from '../utils/trainerMoves'

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

const SEEN_COLOR = '#5ba85b'
const ESTIMATE_COLOR = '#f2b46b'

// The root font sets an absolute line-height that every descendant
// inherits, so these small lines need their own or each takes 26px.
const TIGHT_LINE = 1.2

// The four moves under each opponent in the team list: type and name
// only, seen moves tagged and in green. Detail (category, power,
// accuracy) lives in the comparison panel once the Pokémon is selected.
function OpponentMoveList({ slots }) {
  if (slots.length === 0) {
    return <div style={{ fontSize: '0.68em', lineHeight: TIGHT_LINE, color: 'var(--text-secondary)' }}>No moves</div>
  }
  return (
    <div className="battle-compare__moves" style={{ display: 'grid', gap: '3px' }}>
      {slots.map((move, idx) => (
        <div
          key={`${move.move_name}-${idx}`}
          title={move.seen ? `${move.move_name} (seen in play)` : move.move_name}
          style={{ display: 'flex', alignItems: 'center', gap: '5px', minWidth: 0, fontSize: '0.7em', lineHeight: TIGHT_LINE, color: move.seen ? SEEN_COLOR : 'var(--text-primary)' }}
        >
          {move.type ? <TypeIcon type={move.type} height={12} /> : <span style={{ width: '12px', flexShrink: 0 }} />}
          <span className="battle-compare__move-name" style={{ minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{move.move_name}</span>
          {move.seen && <span className="battle-compare__seen" style={{ flexShrink: 0, fontSize: '0.85em' }}>seen</span>}
        </div>
      ))}
    </div>
  )
}

// Full move rows for the selected opponent, under its stats.
function OpponentMoveDetail({ mon }) {
  const slots = battleMoveSlots(mon)
  const estimated = hasEstimatedMoves(mon, slots)
  return (
    <div className="battle-compare__move-detail" style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '8px', fontSize: '0.72em', marginBottom: '6px' }}>
        <span style={{ fontWeight: 'bold', color: 'var(--text-secondary)' }}>{mon.species_name} moves</span>
        {estimated && <span style={{ color: ESTIMATE_COLOR }}>*Estimated</span>}
      </div>
      {slots.length === 0 ? (
        <div style={{ fontSize: '0.76em', color: 'var(--text-secondary)' }}>No moves</div>
      ) : (
        <div style={{ display: 'grid', gap: '4px' }}>
          {slots.map((move, idx) => (
            <div
              key={`${move.move_name}-${idx}`}
              className="battle-compare__move-row"
              style={{
                // type sprites are 32x12: the column holds one at natural size
                display: 'grid', gridTemplateColumns: '32px minmax(0, 1fr) 28px 54px 54px', columnGap: '8px', alignItems: 'center',
                fontSize: '0.76em', lineHeight: 1.3, padding: '4px 8px', borderRadius: '6px', background: 'var(--surface-deep)',
                border: `1px solid ${move.seen ? SEEN_COLOR : 'var(--border-strong)'}`,
              }}
            >
              {move.type ? <TypeIcon type={move.type} height={12} /> : <span />}
              <span style={{ display: 'flex', alignItems: 'baseline', gap: '5px', minWidth: 0 }}>
                <span className="battle-compare__move-name" style={{ minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: 'var(--text-primary)', fontWeight: 'bold' }}>
                  {move.move_name}
                </span>
                {move.seen && <span className="battle-compare__seen" style={{ flexShrink: 0, color: SEEN_COLOR }}>seen</span>}
              </span>
              {move.damage_class ? (
                <img
                  src={`/sprites/types/${String(move.damage_class).toLowerCase()}.png`}
                  alt={move.damage_class}
                  title={move.damage_class}
                  style={{ height: '16px', width: 'auto', justifySelf: 'center' }}
                  onError={(e) => { e.currentTarget.style.visibility = 'hidden' }}
                />
              ) : <span />}
              <span style={{ color: 'var(--text-secondary)' }}>Pow {move.power ?? '—'}</span>
              <span style={{ color: 'var(--text-secondary)' }}>Acc {move.accuracy ?? '—'}</span>
            </div>
          ))}
        </div>
      )}
    </div>
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
  faintedIds = [],
  onToggleFainted = null,
  onDeclareDefeat = null,
  defeatSaving = false,
  defeatError = '',
  battleType = null,
  gameId = null,
  levelCap = null,
}) {
  const [selectedPlayer, setSelectedPlayer] = useState(null)
  const [selectedOpponent, setSelectedOpponent] = useState(null)
  const [confirmingDefeat, setConfirmingDefeat] = useState(false)
  const [calcNote, setCalcNote] = useState('')

  const damageCalc = getDamageCalc(gameId)

  useEffect(() => {
    if (damageCalc) prefetchDexPatch(gameId)
  }, [damageCalc, gameId])

  const openDamageCalc = async () => {
    if (!damageCalc || playerParty.length === 0) return
    // Lockley does not track current levels; the battle's cap is the
    // Nuzlocke default, falling back to the opponent's highest level.
    const opponentMax = opponentParty.reduce((max, m) => Math.max(max, Number(m?.lvl) || 0), 0)
    const level = Number(levelCap) > 0 ? Number(levelCap) : (opponentMax || null)
    const ok = await openCalcWithTeams(playerParty, opponentParty, trainerName, level, damageCalc.gen, gameId, subtitle)
    setCalcNote(!ok
      ? 'Could not store the teams — browser storage is blocked.'
      : ok.patched
        ? 'Both teams loaded, with this game’s modified Pokémon applied.'
        : 'Both teams are loaded in the calc’s set lists.')
  }

  // The modal renders inside the trainer card, whose root click handler
  // toggles the card open/shut. Without a scroll lock the page behind
  // also scrolls under a touch drag once the modal's own list hits its end.
  useEffect(() => {
    const { body } = document
    const previousOverflow = body.style.overflow
    const previousOverscroll = body.style.overscrollBehavior
    body.style.overflow = 'hidden'
    body.style.overscrollBehavior = 'contain'
    return () => {
      body.style.overflow = previousOverflow
      body.style.overscrollBehavior = previousOverscroll
    }
  }, [])

  // On the stacked phone layout the comparison panel sits below both
  // party lists, so a tap on a Pokémon would otherwise change nothing
  // in view.
  const comparisonRef = useRef(null)
  useEffect(() => {
    if (selectedPlayer == null && selectedOpponent == null) return
    const panel = comparisonRef.current
    if (!panel || typeof panel.scrollIntoView !== 'function') return
    if (!window.matchMedia?.('(max-width: 640px)')?.matches) return
    panel.scrollIntoView({ block: 'start', behavior: 'smooth' })
  }, [selectedPlayer, selectedOpponent])

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
      onClick={event => {
        // This modal is a descendant of the trainer card in the React
        // tree, so a backdrop tap would bubble up and collapse the card
        // as well as closing the modal, throwing away the loaded party.
        event.stopPropagation()
        onClose()
      }}
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
          <div ref={comparisonRef} className="battle-compare__comparison" style={{ border: '1px solid var(--border-strong)', borderRadius: '8px', padding: '14px' }}>
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
                <OpponentMoveDetail mon={opponentMon} />
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
                    {!isPlayer && <OpponentMoveDetail mon={mon} />}
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
                {opponentParty.map((mon, idx) => {
                  const slots = battleMoveSlots(mon)
                  const estimated = hasEstimatedMoves(mon, slots)
                  return (
                    <button
                      type="button"
                      key={`${mon.species_id}-${idx}`}
                      onClick={() => toggleOpponent(idx)}
                      style={{
                        ...PARTY_SELECT_BUTTON_STYLE,
                        borderRadius: '10px',
                        flexDirection: 'column',
                        alignItems: 'stretch',
                        gap: '5px',
                        padding: '6px 8px',
                        borderColor: selectedOpponent === idx ? ESTIMATE_COLOR : 'var(--border-strong)',
                        background: selectedOpponent === idx ? 'rgba(242,180,107,0.08)' : 'var(--surface-deep)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '7px', minWidth: 0 }}>
                        <Sprite speciesId={mon.species_id} size={34} />
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontSize: '0.8em', lineHeight: TIGHT_LINE, fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {mon.species_name}
                          </div>
                          <div style={{ fontSize: '0.68em', lineHeight: TIGHT_LINE, marginTop: '2px', color: 'var(--text-secondary)', minWidth: 0 }}>
                            Lvl {mon.lvl}
                            {estimated && (
                              <span style={{ color: ESTIMATE_COLOR }} title="Moves estimated from the level-up learnset"> · est. moves</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <OpponentMoveList slots={slots} />
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {onToggleFainted && playerParty.length > 0 && !defeated && !battleResult?.success && (
          <fieldset className="battle-casualties" disabled={battleSaving || battleLoading}>
            <legend>Fell in this battle</legend>
            <div>{playerParty.map(mon => (
              <label key={mon.pokemon_id}>
                <input type="checkbox" checked={faintedIds.includes(Number(mon.pokemon_id))}
                  onChange={() => onToggleFainted(Number(mon.pokemon_id))} />
                <Sprite speciesId={mon.species_id} size={28} />
                {mon.nickname || mon.species_name}
              </label>
            ))}</div>
            {faintedIds.length > 0 && <small>These Pokémon will be marked fallen when you record victory.</small>}
          </fieldset>
        )}
        {battleResult?.error && <p role="alert" style={{ color: 'var(--danger, #e05252)' }}>{battleResult.error}</p>}
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
            <Button
              tone={damageCalc ? 'info' : 'neutral'}
              onClick={openDamageCalc}
              disabled={!damageCalc || battleLoading || playerParty.length === 0}
              title={damageCalc
                ? 'Open the damage calculator with both teams already loaded'
                : 'Damage calc is set up for Blaze Black first — other games are coming'}
            >
              Damage Calc
            </Button>
            {calcNote && (
              <span style={{ fontSize: '0.75em', color: '#7ec8e3', maxWidth: '340px' }}>{calcNote}</span>
            )}
            {onDeclareDefeat && !battleResult?.success && (
              confirmingDefeat ? (
                <>
                  <span style={{ fontSize: '0.78em', color: '#e05252' }}>
                    End this attempt? {trainerName} is recorded as the killer and your party is marked fallen.
                  </span>
                  <Button onClick={() => setConfirmingDefeat(false)} disabled={defeatSaving}>
                    Cancel
                  </Button>
                  <Button tone="danger" onClick={onDeclareDefeat} disabled={defeatSaving} style={defeatSaving ? { cursor: 'wait' } : undefined}>
                    {defeatSaving ? 'Ending...' : '☠ Confirm Defeat'}
                  </Button>
                </>
              ) : (
                <Button tone="danger" appearance="outline" onClick={() => setConfirmingDefeat(true)} title="Lost this battle? End the attempt and record the killer.">
                  Declare Defeat
                </Button>
              )
            )}
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
          <Button onClick={onClose}>Back</Button>
          {/* The screen's one main action. */}
          <Button
            tone={(defeated || battleResult?.success) ? 'neutral' : 'success'}
            appearance={(defeated || battleResult?.success) ? 'tinted' : 'solid'}
            onClick={onMarkVictory}
            disabled={defeated || battleSaving || battleLoading || battleResult?.success || !!battleResult?.partyLoadFailed}
          >
            {defeated || battleResult?.success ? '✓ Victory' : battleSaving ? 'Saving...' : 'Mark Victory'}
          </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default BattleCompareModal
