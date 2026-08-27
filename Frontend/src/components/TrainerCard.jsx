import { useState, useEffect, useRef } from 'react'
import Sprite from './Sprite'
import TypeIcon, { TypeIconRow } from './TypeIcon'
import PokemonStatRows from './PokemonStatRows'
import { getTrainerSpriteSrc } from './trainerSprite'
import BattleCompareModal from './BattleCompareModal'
import BattleFormatPill, { normalizeBattleFormat } from './BattleFormatPill'
import { apiFetch } from '../utils/api'
import { getParty, markTrainerVictory, endAttempt } from '../utils/dataLayer'
import { useAuth } from '../contexts/AuthContext'

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

function TrainerCard({ encounterName, trainerName, trainerClass, trainerPic = null, trainerItems = '', encounterTitle = '', showLevelCap = false, levelCap = null, typeFocus = null, hideClass = false, gameId = null, generation = null, versionGroupId = null, runId = null, attemptId = null, trainerId = null, bossEventId = null, badgeId = null, enableBattle = false, isDefeated = false, onVictoryRecorded = null, attemptEnded = false, battleType = null }) {
  const { user } = useAuth()
  const isAdmin = user?.account_type === 'admin'
  const [open, setOpen] = useState(false)
  const [party, setParty] = useState([])
  const [partyLoaded, setPartyLoaded] = useState(false)
  const [moveDraft, setMoveDraft] = useState({})
  const [moveSuggestions, setMoveSuggestions] = useState([])
  const [moveSaving, setMoveSaving] = useState({})
  const [moveError, setMoveError] = useState({})
  const moveSuggestSeqRef = useRef(0)
  const suppressToggleRef = useRef(false)
  const [showBattleModal, setShowBattleModal] = useState(false)
  const [playerParty, setPlayerParty] = useState([])
  const [battleLoading, setBattleLoading] = useState(false)
  const [battleSaving, setBattleSaving] = useState(false)
  const [battleResult, setBattleResult] = useState(null)
  const [defeated, setDefeated] = useState(Boolean(isDefeated))
  const [defeatSaving, setDefeatSaving] = useState(false)
  const [defeatError, setDefeatError] = useState('')

  useEffect(() => {
    setDefeated(Boolean(isDefeated))
  }, [isDefeated])

  useEffect(() => {
    setParty([])
    setPartyLoaded(false)
  }, [encounterName, gameId, trainerId])

  useEffect(() => {
    const hasTrainerId = trainerId !== null && trainerId !== undefined && trainerId !== ''
    if ((!encounterName && !hasTrainerId) || partyLoaded) return

    const controller = new AbortController()
    const query = gameId ? `?game_id=${gameId}` : ''
    const partyUrl = hasTrainerId
      ? `/api/trainers/${trainerId}/party${query}`
      : `/api/trainer-party/${encodeURIComponent(encounterName)}${query}`
    apiFetch(partyUrl, { signal: controller.signal })
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
  }, [encounterName, gameId, trainerId, partyLoaded])

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
  const numericLevelCap = levelCap !== null && levelCap !== undefined && levelCap !== ''
    ? Number(levelCap)
    : null
  const resolvedLevelCap = Number.isFinite(numericLevelCap)
    ? numericLevelCap
    : (party.length > 0 ? Math.max(...party.map(p => Number(p.lvl) || 0)) : null)

  const openBattleModal = (event) => {
    event.stopPropagation()
    if (defeated) return
    if (!runId || !attemptId) return
    setDefeatError('')
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
    setDefeatError('')
  }

  const fetchMoveSuggestions = (text) => {
    const q = (text || '').trim()
    if (q.length < 2) return
    const seq = ++moveSuggestSeqRef.current
    apiFetch(`/api/moves/search?q=${encodeURIComponent(q)}`)
      .then(res => res.json())
      .then(data => {
        if (seq !== moveSuggestSeqRef.current) return
        setMoveSuggestions(Array.isArray(data) ? data : [])
      })
      .catch(() => {})
  }

  const addObservedMove = (slot, moveNameOverride) => {
    const text = (moveNameOverride != null ? moveNameOverride : (moveDraft[slot] || '')).trim()
    if (!text || trainerId == null || moveSaving[slot]) return
    setMoveSaving(prev => ({ ...prev, [slot]: true }))
    setMoveError(prev => ({ ...prev, [slot]: null }))
    apiFetch('/api/admin/trainer-moves', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trainer_id: trainerId, slot, move_name: text }),
    })
      .then(async res => {
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(data.error || `Save failed (${res.status})`)
        return data
      })
      .then(data => {
        const added = data.move
        setParty(prev => prev.map(member => member.slot === slot
          ? {
              ...member,
              observed_moves: [
                ...(member.observed_moves || []).filter(m =>
                  (m.move_name || '').toLowerCase() !== (added.move_name || '').toLowerCase()),
                added,
              ],
            }
          : member))
        if (moveNameOverride == null) setMoveDraft(prev => ({ ...prev, [slot]: '' }))
      })
      .catch(err => {
        console.error('Failed to record observed move:', err)
        setMoveError(prev => ({ ...prev, [slot]: err.message || 'Save failed' }))
      })
      .finally(() => setMoveSaving(prev => ({ ...prev, [slot]: false })))
  }

  const removeObservedMove = (slot, moveName) => {
    if (trainerId == null) return
    setMoveError(prev => ({ ...prev, [slot]: null }))
    apiFetch('/api/admin/trainer-moves', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trainer_id: trainerId, slot, move_name: moveName }),
    })
      .then(async res => {
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(data.error || `Remove failed (${res.status})`)
        if (!data.removed) throw new Error('Nothing removed; refresh and retry')
        setParty(prev => prev.map(member => member.slot === slot
          ? {
              ...member,
              observed_moves: (member.observed_moves || []).filter(m =>
                (m.move_name || '').toLowerCase() !== (moveName || '').toLowerCase()),
            }
          : member))
      })
      .catch(err => {
        console.error('Failed to remove observed move:', err)
        setMoveError(prev => ({ ...prev, [slot]: err.message || 'Remove failed' }))
      })
  }

  const declareDefeat = () => {
    if (!runId || !attemptId || defeatSaving) return
    setDefeatSaving(true)
    setDefeatError('')
    endAttempt(runId, attemptId, {
      trainerId: trainerId != null && trainerId !== '' ? Number(trainerId) : null,
      trainerName: trainerName || encounterName || null,
      trainerClass: trainerClass || null,
    })
      .then(() => { window.location.href = `/attempt/${runId}/${attemptId}/summary` })
      .catch(err => {
        console.error('Failed to declare defeat:', err)
        setDefeatError(err.message || 'Failed to end attempt')
        setDefeatSaving(false)
      })
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
      className="trainer-card"
      style={{ border: '1px solid var(--border-strong)', borderRadius: '12px', padding: '8px', cursor: 'pointer', userSelect: 'none', overflow: 'hidden', background: 'var(--surface)', boxShadow: '0 2px 6px rgba(0,0,0,0.4)' }}
      onMouseDown={(event) => {
        // A drag that starts in an interactive control (text selection in the
        // add-move input) composes its click on this root; remember the press
        // origin so that composed click cannot toggle the card.
        suppressToggleRef.current = Boolean(event.target.closest('input, button, select, textarea, a, label, datalist'))
      }}
      onClick={(event) => {
        if (suppressToggleRef.current) { suppressToggleRef.current = false; return }
        if (event.target.closest('input, button, select, textarea, a, label, datalist')) return
        const nextOpen = !open
        setOpen(nextOpen)
        if (nextOpen && party.length === 0) {
          // If a prior load failed, retry when the card is reopened.
          setPartyLoaded(false)
        }
      }}
    >
      <div
        className="trainer-card-summary"
      >

        {/* Trainer sprite */}
        {(() => {
          const src = getTrainerSpriteSrc(trainerPic, trainerClass, trainerName, gameId, versionGroupId, generation)
          return src
            ? <img className="trainer-card-summary__sprite" src={src} style={{ height: '80px', width: 'auto', flexShrink: 0, imageRendering: 'pixelated', objectFit: 'contain' }}
                alt={trainerName || formattedClass}
                onError={e => { e.currentTarget.style.visibility = 'hidden' }} />
            : <div className="trainer-card-summary__sprite" style={{ width: '40px', height: '80px', flexShrink: 0 }} />
        })()}

        {/* Trainer name + title */}
        <div className="trainer-card-summary__identity" style={{ minWidth: '130px', display: 'grid', gridTemplateColumns: 'minmax(0, auto) auto', alignItems: 'center', justifyContent: 'start', columnGap: '8px' }}>
          <div style={{ fontWeight: 'bold', color: 'var(--text-primary)' }}>{trainerName || '—'}</div>
          {typeFocus && <TypeIcon type={typeFocus} height={18} />}
          <div style={{ gridColumn: '1 / -1', fontSize: '0.8em', color: 'var(--text-secondary)', marginTop: '2px' }}>{subtitle}</div>
        </div>

        {/* 6 pokemon slot placeholders — hidden when expanded */}
        {!open && (
          <div className="trainer-card-summary__party" style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
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
          <div className="trainer-card-summary__items" style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
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

        {/* The format pill shares the level-cap grid cell: it sits left of
            the cap and can never wrap onto a row of its own in any of the
            summary's three grid templates. */}
        {(normalizeBattleFormat(battleType) || (showLevelCap && resolvedLevelCap !== null)) && (
          <div className="trainer-card-summary__cap" style={{ marginRight: '12px', display: 'inline-flex', alignItems: 'center', justifyContent: 'flex-end', gap: '10px', flexShrink: 0 }}>
            <BattleFormatPill format={battleType} fontSize="0.72em" />
            {showLevelCap && resolvedLevelCap !== null && (
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '0.7em', color: 'var(--text-secondary)' }}>Level Cap</div>
                <div style={{ fontWeight: 'bold', fontSize: '1.1em' }}>
                  Lvl {resolvedLevelCap}
                </div>
              </div>
            )}
          </div>
        )}

        {enableBattle && runId && attemptId && trainerId && (defeated || !attemptEnded) && (
          defeated ? (
            <div className="trainer-card-summary__battle" style={{ minHeight: '34px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: '6px 10px', fontSize: '0.78em', color: '#5ba85b', border: '1px solid #5ba85b', borderRadius: '999px', background: 'rgba(91,168,91,0.12)', flexShrink: 0, boxSizing: 'border-box' }}>
              Defeated
            </div>
          ) : (
            <button
              className="trainer-card-summary__battle"
              type="button"
              onClick={openBattleModal}
              style={{ minHeight: '34px', padding: '6px 10px', border: '1px solid #7ec8e3', borderRadius: '999px', background: 'rgba(126,200,227,0.12)', color: '#7ec8e3', cursor: 'pointer', font: 'inherit', fontSize: '0.78em', flexShrink: 0 }}
            >
              Battle
            </button>
          )
        )}

        <div className="trainer-card-summary__chevron" style={{ fontSize: '0.8em', color: 'var(--text-secondary)', flexShrink: 0, marginLeft: '8px' }}>
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

                  {/* Moves: observed (ground truth recorded in play) first,
                      then inferred moves that observation hasn't confirmed. */}
                  {(() => {
                    const observed = p.observed_moves || []
                    const observedNames = new Set(observed.map(m => (m.move_name || '').toLowerCase()))
                    // A Pokemon holds four moves: confirmed sightings claim
                    // their slots first, estimates only fill what remains.
                    const inferred = (p.resolved_moves || movesList).filter(move => typeof move === 'string'
                      ? !observedNames.has(move.toLowerCase())
                      : !observedNames.has((move.move_name || '').toLowerCase()))
                      .slice(0, Math.max(0, 4 - observed.length))
                    const renderMoveRow = (move, idx, seen) => {
                      if (typeof move === 'string') {
                        return <div key={idx} style={{ fontSize: '0.78em', color: 'var(--text-primary)', marginBottom: '4px' }}>{move}</div>
                      }
                      return (
                        <div key={`${seen ? 'seen' : 'inf'}-${move.move_id ?? move.move_name}-${idx}`} style={{ position: 'relative', border: seen ? '1px solid #5ba85b' : '1px solid var(--border-strong)', borderRadius: '5px', padding: '6px 28px 5px 8px', marginBottom: '3px', background: 'var(--surface-mid)', minHeight: '30px' }}>
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
                          <div style={{ fontSize: '0.75em', color: 'var(--text-primary)', fontWeight: 'bold', lineHeight: 1.12, paddingRight: '2px' }}>
                            {move.move_name}
                            {seen && <span style={{ marginLeft: '5px', fontSize: '0.85em', fontWeight: 'normal', color: '#5ba85b' }}>seen</span>}
                          </div>
                          <div style={{ display: 'flex', gap: '5px', marginTop: '2px', fontSize: '0.7em', color: 'var(--text-secondary)', flexWrap: 'wrap', alignItems: 'center' }}>
                            {move.type && <TypeIcon type={move.type} height={14} />}
                            <span>Pow {move.power ?? '—'}</span>
                            <span>Acc {move.accuracy ?? '—'}</span>
                          </div>
                          {seen && isAdmin && (
                            <button
                              type="button"
                              onClick={(e) => { e.stopPropagation(); removeObservedMove(p.slot, move.move_name) }}
                              title="Remove observed move"
                              style={{ position: 'absolute', top: '2px', right: '2px', border: 'none', background: 'transparent', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.72em', lineHeight: 1, padding: '2px' }}
                            >
                              ✕
                            </button>
                          )}
                          {!seen && isAdmin && trainerId != null && p.slot != null && (
                            <button
                              type="button"
                              onClick={(e) => { e.stopPropagation(); addObservedMove(p.slot, move.move_name) }}
                              title="Confirm this move was seen"
                              disabled={Boolean(moveSaving[p.slot])}
                              style={{ position: 'absolute', top: '2px', right: '2px', border: 'none', background: 'transparent', color: '#5ba85b', cursor: moveSaving[p.slot] ? 'wait' : 'pointer', fontSize: '0.72em', lineHeight: 1, padding: '2px' }}
                            >
                              ✓
                            </button>
                          )}
                        </div>
                      )
                    }
                    return (
                      <div style={{ minWidth: 0, border: '1px solid var(--border-strong)', borderRadius: '6px', padding: '7px', background: 'var(--surface-mid)' }}>
                        {p.moves_estimated && inferred.length > 0 && (
                          <div style={{ fontSize: '0.7em', color: '#f2b46b', marginBottom: '5px' }}>*Estimated</div>
                        )}
                        {observed.map((move, idx) => renderMoveRow(move, idx, true))}
                        {inferred.map((move, idx) => renderMoveRow(move, idx, false))}
                        {observed.length === 0 && inferred.length === 0 && (
                          <div style={{ fontSize: '0.78em', color: 'var(--text-secondary)' }}>No moves</div>
                        )}
                        {isAdmin && trainerId != null && p.slot != null && (
                          <div onClick={(e) => e.stopPropagation()} style={{ marginTop: '5px' }}>
                            <div style={{ display: 'flex', gap: '4px' }}>
                              <input
                                type="text"
                                value={moveDraft[p.slot] || ''}
                                list={`observed-moves-${trainerId}-${p.slot}`}
                                placeholder="Add seen move"
                                onChange={(e) => { setMoveDraft(prev => ({ ...prev, [p.slot]: e.target.value })); setMoveError(prev => ({ ...prev, [p.slot]: null })); fetchMoveSuggestions(e.target.value) }}
                                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addObservedMove(p.slot) } }}
                                style={{ flex: 1, minWidth: 0, fontSize: '0.72em', padding: '4px 6px', borderRadius: '5px', border: '1px solid var(--border-strong)', background: 'var(--surface-deep)', color: 'var(--text-primary)' }}
                              />
                              <datalist id={`observed-moves-${trainerId}-${p.slot}`}>
                                {moveSuggestions.map(name => <option key={name} value={name} />)}
                              </datalist>
                              <button
                                type="button"
                                disabled={Boolean(moveSaving[p.slot]) || !(moveDraft[p.slot] || '').trim()}
                                onClick={(e) => { e.stopPropagation(); addObservedMove(p.slot) }}
                                style={{ fontSize: '0.72em', padding: '4px 8px', borderRadius: '5px', border: '1px solid #5ba85b', background: 'rgba(91,168,91,0.12)', color: '#5ba85b', cursor: moveSaving[p.slot] ? 'wait' : 'pointer' }}
                              >
                                Add
                              </button>
                            </div>
                            {moveError[p.slot] && (
                              <div style={{ fontSize: '0.68em', color: '#e05252', marginTop: '3px' }}>{moveError[p.slot]}</div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })()}

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
          onDeclareDefeat={runId && attemptId ? declareDefeat : null}
          defeatSaving={defeatSaving}
          defeatError={defeatError}
          battleType={battleType}
        />
      )}
    </div>
  )
}

export default TrainerCard
