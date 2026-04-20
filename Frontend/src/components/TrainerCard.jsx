import { useState, useEffect } from 'react'
import Sprite from './Sprite'
import TypeIcon, { TypeIconRow } from './TypeIcon'
import PokemonStatRows from './PokemonStatRows'
import { getTrainerSpriteSrc } from './trainerSprite'
import BattleCompareModal from './BattleCompareModal'

function normalizeItemName(raw) {
  const token = String(raw || '').trim()
  if (!token) return null

  // Handles SQL-ish arrays, JSON strings, and quoted constants like "'ITEM_FULL_RESTORE'".
  const cleaned = token
    .replace(/^[\s{[("']+/, '')
    .replace(/[\s})\]("']+$/, '')
    .replace(/^ITEM_/i, '')
    .trim()

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

function TrainerCard({ encounterName, trainerName, trainerClass, trainerItems = '', encounterTitle = '', showLevelCap = false, gameId = null, runId = null, attemptId = null, trainerId = null, enableBattle = false, isDefeated = false, onVictoryRecorded = null }) {
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
    fetch(`/api/trainer-party/${encodeURIComponent(encounterName)}${query}`, { signal: controller.signal })
      .then(res => res.json())
      .then(data => {
        setParty(data)
        setPartyLoaded(true)
      })
      .catch(err => {
        if (err.name === 'AbortError') return
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
  const subtitle = normalizedClass && normalizedTitle && normalizedClass === normalizedTitle
    ? formattedClass
    : [formattedClass, encounterTitle].filter(Boolean).join(' - ')
  const itemTokens = parseTrainerItems(trainerItems)

  const openBattleModal = (event) => {
    event.stopPropagation()
    if (defeated) return
    if (!runId || !attemptId) return
    setBattleResult(null)
    setShowBattleModal(true)
    setBattleLoading(true)
    fetch(`/api/runs/${runId}/attempts/${attemptId}/party`)
      .then(res => res.json())
      .then(data => setPlayerParty(data))
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
    fetch(`/api/runs/${runId}/attempts/${attemptId}/trainer-victory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        trainer_id: trainerId,
        trainer_name: encounterName,
        trainer_class: trainerClass,
        encounter_title: encounterTitle,
      })
    })
      .then(res => res.json())
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
      style={{ border: '1px solid #ccc', padding: '8px', cursor: 'pointer', userSelect: 'none' }}
      onClick={() => setOpen(!open)}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>

        {/* Trainer sprite */}
        {(() => {
          const src = getTrainerSpriteSrc(trainerClass, trainerName)
          return src
            ? <img src={src} style={{ height: '80px', width: 'auto', flexShrink: 0, imageRendering: 'pixelated', objectFit: 'contain' }}
                alt={trainerName || formattedClass}
                onError={e => { e.currentTarget.style.visibility = 'hidden' }} />
            : <div style={{ width: '40px', height: '80px', flexShrink: 0 }} />
        })()}

        {/* Trainer name + title */}
        <div style={{ minWidth: '130px' }}>
          <div style={{ fontWeight: 'bold' }}>{trainerName || '—'}</div>
          <div style={{ fontSize: '0.8em', color: '#999', marginTop: '2px' }}>{subtitle}</div>
        </div>

        {/* 6 pokemon slot placeholders — hidden when expanded */}
        {!open && (
          <div style={{ display: 'flex', gap: '6px' }}>
            {Array.from({ length: 6 }, (_, i) => {
              const pokemon = party[i]
              return (
                <div key={i} style={{
                  width: '48px', height: '48px', border: '1px solid #555',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '0.65em', textAlign: 'center', color: '#aaa'
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
            <div style={{ fontSize: '0.7em', color: '#888' }}>Level Cap</div>
            <div style={{ fontWeight: 'bold', fontSize: '1.1em' }}>
              Lvl {Math.max(...party.map(p => p.lvl))}
            </div>
          </div>
        )}

        {enableBattle && runId && attemptId && trainerId && (
          defeated ? (
            <div style={{ padding: '4px 10px', fontSize: '0.78em', color: '#5ba85b', border: '1px solid #5ba85b', borderRadius: '4px', flexShrink: 0 }}>
              Defeated
            </div>
          ) : (
            <button
              onClick={openBattleModal}
              style={{ padding: '4px 10px', fontSize: '0.78em', cursor: 'pointer', color: '#7ec8e3', borderColor: '#7ec8e3', flexShrink: 0 }}
            >
              Battle
            </button>
          )
        )}

        <div style={{ fontSize: '0.8em', color: '#888', flexShrink: 0, marginLeft: '8px' }}>
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
              <div key={i} style={{ border: '1px solid #444', borderRadius: '4px', overflow: 'hidden' }}>

                {/* Pokemon card header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '6px 8px', borderBottom: '1px solid #444', backgroundColor: '#1e1f26' }}>
                  <Sprite speciesId={p.species_id} size={64} />
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <div style={{ fontWeight: 'bold' }}>
                        {p.species_name} <span style={{ fontWeight: 'normal', fontSize: '0.85em', color: '#aaa' }}>Lvl {p.lvl}</span>
                      </div>
                      {normalizeItemName(p.held_item) && (() => {
                        const heldItem = normalizeItemName(p.held_item)
                        const heldItemSprite = toItemSpriteFile(heldItem)
                        if (!heldItemSprite) return null
                        return (
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.75em', color: '#cfd3de' }} title={displayItemName(heldItem)}>
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
                  <div style={{ minWidth: 0, border: '1px solid #2e2f38', borderRadius: '6px', padding: '7px', background: '#161a21' }}>
                    {p.moves_estimated && (
                      <div style={{ fontSize: '0.7em', color: '#f2b46b', marginBottom: '5px' }}>*Estimated</div>
                    )}
                    {(p.resolved_moves || movesList).length > 0
                      ? (p.resolved_moves || movesList).map((move, idx) => {
                          if (typeof move === 'string') {
                            return <div key={idx} style={{ fontSize: '0.78em', color: '#ccc', marginBottom: '4px' }}>{move}</div>
                          }
                          return (
                            <div key={`${move.move_id}-${idx}`} style={{ position: 'relative', border: '1px solid #262c36', borderRadius: '5px', padding: '6px 28px 5px 8px', marginBottom: '3px', background: '#11151b', minHeight: '30px' }}>
                              {move.type && (
                                <div style={{ position: 'absolute', top: '50%', right: '16px', transform: 'translateY(-50%)', display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                                  <TypeIcon type={move.type} height={14} />
                                </div>
                              )}
                              <div style={{ fontSize: '0.75em', color: '#ddd', fontWeight: 'bold', lineHeight: 1.12, paddingRight: '2px' }}>{move.move_name}</div>
                              <div style={{ display: 'flex', gap: '5px', marginTop: '2px', fontSize: '0.7em', color: '#98a1b2', flexWrap: 'wrap' }}>
                                <span>{move.damage_class || 'Status'}</span>
                                <span>Pow {move.power ?? '—'}</span>
                                <span>Acc {move.accuracy ?? '—'}</span>
                              </div>
                            </div>
                          )
                        })
                      : <div style={{ fontSize: '0.78em', color: '#666' }}>No moves</div>
                    }
                  </div>

                  {/* Stats */}
                  <div style={{ minWidth: 0, fontSize: '0.8em', border: '1px solid #2e2f38', borderRadius: '6px', padding: '7px', background: '#161a21' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '44px 26px 1fr', columnGap: '4px', alignItems: 'center', padding: '0 0 5px 0', marginBottom: '4px', borderBottom: '1px solid #262c36' }}>
                      <span style={{ fontSize: '0.68em', fontWeight: 'bold', color: '#9ca0ad', textAlign: 'left' }}>BST</span>
                      <span style={{ fontSize: '0.72em', fontWeight: 'bold', color: '#eef2f7', textAlign: 'right', whiteSpace: 'nowrap' }}>{p.bst ?? '—'}</span>
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
                      trackColor="#2a2b33"
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
