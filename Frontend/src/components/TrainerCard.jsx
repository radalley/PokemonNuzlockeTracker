import { useState, useEffect } from 'react'
import Sprite from './Sprite'
import TypeIcon, { TypeIconRow } from './TypeIcon'
import PokemonStatRows from './PokemonStatRows'
import { getTrainerSpriteSrc } from './trainerSprite'
import BattleCompareModal from './BattleCompareModal'
import { apiFetch } from '../utils/api'
import { getParty, markTrainerVictory } from '../utils/dataLayer'

function normalizeItemName(raw) {
  const token = String(raw || '').trim()
  if (!token) return null

  // Handles SQL-ish arrays, JSON strings, and quoted constants like "'ITEM_FULL_RESTORE'".
  const cleaned = token
    .replace(/^[\s{[("']+/, '')
    .replace(/[\s})\]("']+$/, '')
    .replace(/^ITEM_/i, '')
    .trim()

  if (/^(none|null|no_item|no item)$/i.test(cleaned)) return null

  return cleaned || null
}

function toItemSpriteFile(itemToken) {
  const token = normalizeItemName(itemToken)
  if (!token) return null
  return token.toLowerCase().replace(/_/g, '-')
}

function displayItemName(raw) {
  const token = normalizeItemName(raw)
  if (!token) return ''
  return token.toLowerCase().replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function parseTrainerItems(value) {
  if (value == null) return []
  if (Array.isArray(value)) {
    return value.map(normalizeItemName).filter(Boolean)
  }

  const text = String(value).trim()
  if (!text) return []

  const trimmed = text.replace(/^[\s{[(]+|[\s})\]]+$/g, '')
  return trimmed
    .split(',')
    .map(x => normalizeItemName(x))
    .filter(Boolean)
}

function TrainerCard({ encounterName, trainerName, trainerClass, trainerPic = null, trainerItems = '', encounterTitle = '', showLevelCap = false, hideClass = false, gameId = null, versionGroupId = null, runId = null, attemptId = null, trainerId = null, bossEventId = null, badgeId = null, enableBattle = false, isDefeated = false, onVictoryRecorded = null }) {
  const [open, setOpen] = useState(false)
  const [party, setParty] = useState([])
  const [partyLoaded, setPartyLoaded] = useState(false)
  const [showBattleModal, setShowBattleModal] = useState(false)
  const [playerParty, setPlayerParty] = useState([])
  const [battleLoading, setBattleLoading] = useState(false)
  const [battleSaving, setBattleSaving] = useState(false)
  const [battleResult, setBattleResult] = useState(null)
  const [defeated, setDefeated] = useState(Boolean(isDefeated))

  useEffect(() => {
    setDefeated(Boolean(isDefeated))
  }, [isDefeated])

  useEffect(() => {
    setParty([])
    setPartyLoaded(false)
  }, [encounterName, gameId])

  useEffect(() => {
    if (!encounterName || partyLoaded) return

    const controller = new AbortController()
    const query = gameId ? `?game_id=${gameId}` : ''
    apiFetch(`/api/trainer-party/${encodeURIComponent(encounterName)}${query}`, { signal: controller.signal })
      .then(async res => {
        if (!res.ok) {
          const text = await res.text().catch(() => '')
          throw new Error(`trainer-party failed ${res.status}: ${text.slice(0, 200)}`)
        }
        return res.json()
      })
      .then(data => {
        setParty(Array.isArray(data) ? data : [])
        setPartyLoaded(true)
      })
      .catch(err => {
        if (err.name === 'AbortError') return
        console.error('Failed to load trainer party:', err)
        setParty([])
        setPartyLoaded(true)
      })

    return () => controller.abort()
  }, [encounterName, gameId, partyLoaded])

  const formattedClass = trainerClass
    ? trainerClass
        .replace('TRAINER_CLASS_', '')
        .replace(/_/g, ' ')
        .toLowerCase()
        .replace(/\b\w/g, c => c.toUpperCase())
    : ''

  const normalizedClass = formattedClass.trim().toLowerCase()
  const normalizedTitle = (encounterTitle || '').trim().toLowerCase()
  const subtitle = hideClass
    ? (encounterTitle || '')
    : normalizedClass && normalizedTitle && normalizedClass === normalizedTitle
      ? formattedClass
      : [formattedClass, encounterTitle].filter(Boolean).join(' - ')
  const itemTokens = parseTrainerItems(trainerItems)
  const displayedParty = party.filter(Boolean)

  const openBattleModal = (event) => {
    event.stopPropagation()
    if (defeated) return
    if (!runId || !attemptId) return
    setBattleResult(null)
    setShowBattleModal(true)
    setBattleLoading(true)
    getParty(runId, attemptId)
      .then(data => setPlayerParty(data || []))
      .finally(() => setBattleLoading(false))
  }

  const closeBattleModal = (event) => {
    if (event) event.stopPropagation()
    setShowBattleModal(false)
    setBattleResult(null)
  }

  const markVictory = (event) => {
    event.stopPropagation()
    if (!runId || !attemptId || !trainerId) return
    setBattleSaving(true)
    markTrainerVictory(runId, attemptId, trainerId, bossEventId, badgeId)
      .then(data => {
        setBattleResult(data)
        if (data?.success) {
          setDefeated(true)
          if (typeof onVictoryRecorded === 'function') {
            onVictoryRecorded()
          }
        }
      })
      .finally(() => setBattleSaving(false))
  }

  return (
    <div
      style={{ border: '1px solid var(--border-strong)', borderRadius: '12px', padding: '8px', cursor: 'pointer', userSelect: 'none', overflow: 'hidden', background: 'var(--surface)', boxShadow: '0 2px 6px rgba(0,0,0,0.4)' }}
      onClick={() => {
        const nextOpen = !open
        setOpen(nextOpen)
        if (nextOpen && party.length === 0) {
          // If a prior load failed, retry when the card is reopened.
          setPartyLoaded(false)
        }
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>

        {/* Trainer sprite */}
        {(() => {
          const src = getTrainerSpriteSrc(trainerPic, trainerClass, trainerName, gameId, versionGroupId)
          return src
            ? <img src={src} style={{ height: '80px', width: 'auto', flexShrink: 0, imageRendering: 'pixelated', objectFit: 'contain' }}
                alt={trainerName || formattedClass}
                onError={e => { e.currentTarget.style.visibility = 'hidden' }} />
            : <div style={{ width: '40px', height: '80px', flexShrink: 0 }} />
        })()}

        {/* Trainer name + title */}
        <div style={{ minWidth: '130px' }}>
          <div style={{ fontWeight: 'bold', color: 'var(--text-primary)' }}>{trainerName || '—'}</div>
          <div style={{ fontSize: '0.8em', color: 'var(--text-secondary)', marginTop: '2px' }}>{subtitle}</div>
        </div>

        {/* 6 pokemon slot placeholders — hidden when expanded */}
        {!open && displayedParty.length > 0 && (
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
            {displayedParty.map((pokemon, i) => {
              return (
                <div key={i} style={{
                  width: '48px', height: '48px', border: '1px solid var(--border-strong)',
                  borderRadius: '10px', background: 'var(--surface-mid)',
                  boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.08)', overflow: 'hidden',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '0.65em', textAlign: 'center', color: 'var(--text-secondary)'
                }}>
                  {pokemon ? <Sprite speciesId={pokemon.species_id} size={40} useIcon /> : '—'}
                </div>
              )
            })}
          </div>
        )}

        {/* Item sprites — always visible on the row */}
        {itemTokens.length > 0 && (
          <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
            {itemTokens.map((itemName, idx) => {
              const spriteFile = toItemSpriteFile(itemName)
              if (!spriteFile) return null
              return (
                <img
                  key={`${itemName}-${idx}`}
                  src={`/sprites/Items/${spriteFile}.png`}
                  alt={displayItemName(itemName)}
                  title={displayItemName(itemName)}
                  style={{ width: '28px', height: '28px', imageRendering: 'pixelated' }}
                  onError={(e) => { e.currentTarget.style.display = 'none' }}
                />
              )
            })}
          </div>
        )}

        {/* Spacer — pushes level cap, button, and chevron to the right */}
        <div style={{ flex: 1 }} />

        {showLevelCap && party.length > 0 && (
          <div style={{ marginRight: '12px', textAlign: 'center', flexShrink: 0 }}>
            <div style={{ fontSize: '0.7em', color: 'var(--text-secondary)' }}>Level Cap</div>
            <div style={{ fontWeight: 'bold', fontSize: '1.1em' }}>
              Lvl {Math.max(...party.map(p => p.lvl))}
            </div>
          </div>
        )}

        {enableBattle && runId && attemptId && trainerId && (
          defeated ? (
            <div style={{ minHeight: '34px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: '6px 10px', fontSize: '0.78em', color: '#5ba85b', border: '1px solid #5ba85b', borderRadius: '999px', background: 'rgba(91,168,91,0.12)', flexShrink: 0, boxSizing: 'border-box' }}>
              Defeated
            </div>
          ) : (
            <button
              type="button"
              onClick={openBattleModal}
              style={{ minHeight: '34px', padding: '6px 10px', border: '1px solid #7ec8e3', borderRadius: '999px', background: 'rgba(126,200,227,0.12)', color: '#7ec8e3', cursor: 'pointer', font: 'inherit', fontSize: '0.78em', flexShrink: 0 }}
            >
              Battle
            </button>
          )
        )}

        <div style={{ fontSize: '0.8em', color: 'var(--text-secondary)', flexShrink: 0, marginLeft: '8px' }}>
          {open ? '▲' : '▼'}
        </div>
      </div>

      {/* Expanded team detail — 2 per row */}
      {open && (
        <>
          {party.length > 0 ? (
            <div style={{
              marginTop: '12px',
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '12px'
            }}>
              {party.map((p, i) => {
            const movesList = p.moves
              ? p.moves.split(',').map(m => m.trim().replace('MOVE_', '').replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase()))
              : []
            const formatType = t => t ? t.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase()) : null
            const formatAbility = a => a ? a.replace(/^ABILITY_/i, '').replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase()) : null
            const type1 = formatType(p.type1)
            const type2 = formatType(p.type2)
            const ability = formatAbility(p.ability1)
            return (
              <div key={i} style={{ border: '1px solid var(--border-strong)', borderRadius: '12px', overflow: 'hidden' }}>

                {/* Pokemon card header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '6px 8px', borderBottom: '1px solid var(--border-strong)', backgroundColor: 'var(--surface-deep)' }}>
                  <Sprite speciesId={p.species_id} size={64} />
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <div style={{ fontWeight: 'bold', color: 'var(--text-primary)' }}>
                        {p.species_name} <span style={{ fontWeight: 'normal', fontSize: '0.85em', color: 'var(--text-secondary)' }}>Lvl {p.lvl}</span>
                      </div>
                      {normalizeItemName(p.held_item) && (() => {
                        const heldItem = normalizeItemName(p.held_item)
                        const heldItemSprite = toItemSpriteFile(heldItem)
                        if (!heldItemSprite) return null
                        return (
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.75em', color: 'var(--text-secondary)' }} title={displayItemName(heldItem)}>
                            <img
                              src={`/sprites/Items/${heldItemSprite}.png`}
                              alt={displayItemName(heldItem)}
                              style={{ width: '20px', height: '20px', imageRendering: 'pixelated' }}
                              onError={(e) => { e.currentTarget.style.display = 'none' }}
                            />
                            <span>{displayItemName(heldItem)}</span>
                          </span>
                        )
                      })()}
                    </div>
                    <div style={{ display: 'flex', gap: '6px', marginTop: '2px', alignItems: 'center', flexWrap: 'wrap' }}>
                      <TypeIconRow types={[type1, type2]} height={20} gap={6} />
                      {ability && (
                        <span style={{fontSize: '1em', }}>
                          {ability}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Pokemon card body — moves left, stats right */}
                <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', padding: '8px', gap: '8px', alignItems: 'stretch' }}>

                  {/* Moves */}
                  <div style={{ minWidth: 0, border: '1px solid var(--border-strong)', borderRadius: '6px', padding: '7px', background: 'var(--surface-mid)' }}>
                    {p.moves_estimated && (
                      <div style={{ fontSize: '0.7em', color: '#f2b46b', marginBottom: '5px' }}>*Estimated</div>
                    )}
                    {(p.resolved_moves || movesList).length > 0
                      ? (p.resolved_moves || movesList).map((move, idx) => {
                          if (typeof move === 'string') {
                            return <div key={idx} style={{ fontSize: '0.78em', color: 'var(--text-primary)', marginBottom: '4px' }}>{move}</div>
                          }
                          return (
                            <div key={`${move.move_id}-${idx}`} style={{ position: 'relative', border: '1px solid var(--border-strong)', borderRadius: '5px', padding: '6px 28px 5px 8px', marginBottom: '3px', background: 'var(--surface-mid)', minHeight: '30px' }}>
                              {move.type && (
                                <div style={{ position: 'absolute', top: '50%', right: '16px', transform: 'translateY(-50%)', display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                                  <img
                                    src={`/sprites/types/${(move.damage_class || 'status').toLowerCase()}.png`}
                                    alt={move.damage_class || 'status'}
                                    height={35}
                                    style={{ height: '35px', width: 'auto', imageRendering: 'auto', flexShrink: 0 }}
                                  />
                                </div>
                              )}
                              <div style={{ fontSize: '0.75em', color: 'var(--text-primary)', fontWeight: 'bold', lineHeight: 1.12, paddingRight: '2px' }}>{move.move_name}</div>
                              <div style={{ display: 'flex', gap: '5px', marginTop: '2px', fontSize: '0.7em', color: 'var(--text-secondary)', flexWrap: 'wrap', alignItems: 'center' }}>
                                {move.type && <TypeIcon type={move.type} height={14} />}
                                <span>Pow {move.power ?? '—'}</span>
                                <span>Acc {move.accuracy ?? '—'}</span>
                              </div>
                            </div>
                          )
                        })
                      : <div style={{ fontSize: '0.78em', color: 'var(--text-secondary)' }}>No moves</div>
                    }
                  </div>

                  {/* Stats */}
                  <div style={{ minWidth: 0, fontSize: '0.8em', border: '1px solid var(--border-strong)', borderRadius: '6px', padding: '7px', background: 'var(--surface-mid)' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '44px 26px 1fr', columnGap: '4px', alignItems: 'center', padding: '0 0 5px 0', marginBottom: '4px', borderBottom: '1px solid var(--border-strong)' }}>
                        <span style={{ fontSize: '0.68em', fontWeight: 'bold', color: 'var(--text-secondary)', textAlign: 'left' }}>BST</span>
                        <span style={{ fontSize: '0.72em', fontWeight: 'bold', color: 'var(--text-primary)', textAlign: 'right', whiteSpace: 'nowrap' }}>{p.bst ?? '—'}</span>
                      <span />
                    </div>
                    <PokemonStatRows
                      stats={p}
                      rowGap="3px"
                      columnGap="4px"
                      labelColumnWidth={44}
                      labelTextWidth={24}
                      modifierWidth={0}
                      valueColumnWidth={26}
                      barHeight={6}
                      labelFontSize="0.68em"
                      valueFontSize="0.72em"
                      labelGap="0px"
                      trackColor="var(--surface-mid)"
                      reserveModifierSpace={false}
                    />
                  </div>
                </div>
              </div>
            )
              })}
            </div>
          ) : (
            <div style={{ marginTop: '10px', fontSize: '0.8em', color: '#888' }}>No trainer party data.</div>
          )}


        </>
      )}

      {showBattleModal && (
        <BattleCompareModal
          playerParty={playerParty}
          opponentParty={party}
          trainerName={trainerName || encounterName}
          subtitle={subtitle}
          battleLoading={battleLoading}
          defeated={defeated}
          battleSaving={battleSaving}
          battleResult={battleResult}
          onClose={closeBattleModal}
          onMarkVictory={markVictory}
        />
      )}
    </div>
  )
}

export default TrainerCard
