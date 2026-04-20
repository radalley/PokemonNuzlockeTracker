import { useState, useEffect } from 'react'
import Sprite from './Sprite'
import { TypeIconRow } from './TypeIcon'
import PokemonStatRows from './PokemonStatRows'

function parseBadgeIds(value) {
  if (!value) return []
  if (Array.isArray(value)) {
    return value.map(v => Number(v)).filter(Number.isFinite)
  }
  if (typeof value === 'number') {
    return Number.isFinite(value) ? [value] : []
  }
  if (typeof value !== 'string') return []

  const trimmed = value.trim()
  if (!trimmed) return []

  try {
    const parsed = JSON.parse(trimmed)
    if (Array.isArray(parsed)) {
      return parsed.map(v => Number(v)).filter(Number.isFinite)
    }
  } catch {
    // Fall back to comma-separated values.
  }

  return trimmed
    .split(',')
    .map(part => Number(part.trim()))
    .filter(Number.isFinite)
}

const STATUS_STYLE = {
  Captured: { color: '#5ba85b', label: 'Captured' },
  Dead:     { color: '#e55',    label: 'Dead' },
  Missed:   { color: '#888',    label: 'Missed' },
}

const BADGE_LEADERS = {
  1: 'Brock',
  2: 'Misty',
  3: 'Lt. Surge',
  4: 'Erika',
  5: 'Koga',
  6: 'Sabrina',
  7: 'Blaine',
  8: 'Giovanni',
}

function PokemonCard({ pokemon, inParty = false, onAddToParty, onRemoveFromParty, onDead, onRevive, onEvolve, runId, attemptId }) {
  const { species_name, nickname, nature, status, shiny, level_met, location_name,
          type1, type2, hp, atk, def, spa, spd, spe, bst } = pokemon
  const displayName = nickname || species_name || '???'
  const hasStats = hp != null

  const statusInfo = STATUS_STYLE[status] || { color: '#aaa', label: status }
  const badgeIds = parseBadgeIds(pokemon.badges_earned)
  const showReviveAction = status === 'Dead' && Boolean(onRevive)
  const showPartyAction = inParty ? Boolean(onRemoveFromParty) : Boolean(onAddToParty)
  const showEvolveAction = Boolean(onEvolve) && status !== 'Dead'
  const showDeadAction = Boolean(onDead) && status !== 'Dead'

  // Dropdown state
  const [showDropdown, setShowDropdown] = useState(false)
  const [trainerData, setTrainerData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [badgeMeta, setBadgeMeta] = useState([])

  useEffect(() => {
    if (badgeIds.length === 0) {
      setBadgeMeta([])
      return
    }
    fetch(`/api/badges?ids=${badgeIds.join(',')}`)
      .then(res => res.json())
      .then(data => setBadgeMeta(Array.isArray(data) ? data : []))
      .catch(() => setBadgeMeta([]))
  }, [pokemon.pokemon_id, badgeIds.join(',')])

  const badgeById = new Map(badgeMeta.map(b => [b.badge_id, b]))

  // Fetch trainer/badge data when dropdown opens
  useEffect(() => {
    if (!showDropdown || !runId || !attemptId || !pokemon.pokemon_id) {
      return
    }
    setLoading(true)
    fetch(`/api/pokemon/${pokemon.pokemon_id}/trainers-badges/${runId}/${attemptId}`)
      .then(res => res.json())
      .then(data => {
        setTrainerData(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch trainer/badge data:', err)
        setLoading(false)
      })
  }, [showDropdown, runId, attemptId, pokemon.pokemon_id])

  return (
    <div style={{
      background: '#1e1f26', border: inParty ? '1px solid #5ba85b' : '1px solid #333', borderRadius: '8px',
      overflow: 'hidden', width: '220px', minWidth: '220px', maxWidth: '220px', boxSizing: 'border-box',
      boxShadow: '0 2px 6px rgba(0,0,0,0.4)',
      opacity: status === 'Dead' ? 0.65 : 1,
      display: 'flex', flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '10px',
        padding: '8px 10px', background: '#25262f', borderBottom: '1px solid #2e2f3a'
      }}>
        {/* Sprite */}
        <div style={{ flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '3px' }}>
          <Sprite speciesId={pokemon.species_id} size={48} shiny={shiny === 'True' || shiny === true} />
          {bst != null && (
            <div style={{ fontSize: '0.6em', color: '#888' }}>BST {bst}</div>
          )}
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <div style={{
              fontWeight: 'bold', fontSize: '0.95em', whiteSpace: 'nowrap',
              overflow: 'hidden', textOverflow: 'ellipsis'
            }}>
              {displayName}
            </div>
            {shiny === 'True' || shiny === true
              ? <span title="Shiny" style={{ fontSize: '0.8em' }}>★</span>
              : null}
          </div>
          <div style={{ fontSize: '0.75em', color: '#aaa', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {species_name || '—'}
          </div>
          <TypeIconRow types={[type1, type2]} height={15} gap={4} style={{ marginTop: '3px' }} />
        </div>
      </div>

      {/* Body */}
      <div style={{ padding: '8px 10px', flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Meta row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', fontSize: '0.72em', color: '#aaa' }}>
          <span style={{ color: statusInfo.color, fontWeight: 'bold' }}>{statusInfo.label}</span>
          <span style={{ color: '#ccc' }}>{nature || '—'}</span>
          {level_met != null && <span>Lv. {level_met}</span>}
        </div>

        <div style={{ marginBottom: '8px', borderTop: '1px solid #2e2f3a', paddingTop: '6px', minHeight: '30px', boxSizing: 'border-box' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', minHeight: '18px', alignItems: 'center' }}>
            {badgeIds.map(badgeId => (
              <img
                key={badgeId}
                src={`/sprites/Badges/${badgeId}.png`}
                alt={badgeById.get(badgeId)?.badge_name || `Badge ${badgeId}`}
                title={badgeById.get(badgeId)?.badge_name || `Badge ${badgeId}`}
                style={{ width: '18px', height: '18px', imageRendering: 'pixelated' }}
              />
            ))}
          </div>
        </div>

        {/* Battle Stats Dropdown */}
        {runId && attemptId && (
          <div style={{ marginBottom: '8px', borderTop: '1px solid #2e2f3a', paddingTop: '6px' }}>
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              style={{
                width: '100%',
                padding: '4px 0',
                fontSize: '0.7em',
                color: '#7ec8e3',
                border: 'none',
                background: 'transparent',
                cursor: 'pointer',
                textAlign: 'left',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span>{showDropdown ? '▼' : '►'}</span>
              <span>Battle Stats</span>
            </button>

            {showDropdown && (
              <div style={{ marginTop: '6px', fontSize: '0.68em', color: '#aaa', paddingLeft: '12px' }}>
                {loading ? (
                  <div>Loading...</div>
                ) : trainerData ? (
                  <div style={{ display: 'grid', gap: '6px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #2e2f3a', paddingBottom: '3px' }}>
                      <span style={{ color: '#9ca0ad' }}>trainers</span>
                      <span style={{ color: '#ddd', fontWeight: 'bold' }}>{trainerData.trainers_defeated_count ?? trainerData.trainers_defeated ?? 0}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #2e2f3a', paddingBottom: '3px' }}>
                      <span style={{ color: '#9ca0ad' }}>bosses</span>
                      <span style={{ color: '#ddd', fontWeight: 'bold' }}>{trainerData.bosses_defeated_count ?? 0}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #2e2f3a', paddingBottom: '3px' }}>
                      <span style={{ color: '#9ca0ad' }}>rivals</span>
                      <span style={{ color: '#ddd', fontWeight: 'bold' }}>{trainerData.rivals_defeated_count ?? 0}</span>
                    </div>

                    <div style={{ marginTop: '2px', color: '#9ca0ad' }}>badges</div>
                    {trainerData.badges_earned?.length > 0 ? (
                      <div style={{ display: 'grid', gap: '4px' }}>
                        {trainerData.badges_earned.map(badge => (
                          <div key={badge.badge_id} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #2e2f3a', paddingBottom: '3px', gap: '8px' }}>
                            <span style={{ color: '#ddd', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {(badge.badge_name || `Badge ${badge.badge_id}`).toLowerCase()}
                            </span>
                            <span style={{ color: '#8ea2bd', fontStyle: 'italic', flexShrink: 0 }}>
                              {(BADGE_LEADERS[badge.badge_id] || 'Leader').toLowerCase()}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ color: '#555' }}>none</div>
                    )}
                  </div>
                ) : (
                  <div style={{ color: '#555' }}>No battle stats yet</div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Stats (hidden while Battle Stats dropdown is open) */}
        {!showDropdown && (
          hasStats ? (
            <PokemonStatRows
              stats={pokemon}
              nature={nature}
              rowGap="4px"
              columnGap="4px"
              rowGridTemplateColumns="10% 14% minmax(0, 1fr)"
              labelTextWidth="100%"
              modifierWidth={24}
              valueColumnWidth={22}
              barHeight={6}
              labelFontSize="0.68em"
              valueFontSize="0.72em"
              labelGap="2px"
              trackColor="#2a2b33"
              reserveModifierSpace={false}
              showNatureModifierText={false}
              colorNatureModifiedLabel
            />
          ) : (
            <div style={{ fontSize: '0.75em', color: '#555', textAlign: 'center', padding: '8px 0' }}>
              No stat data
            </div>
          )
        )}

        <div style={{ marginTop: 'auto' }}>
          {(showReviveAction || showPartyAction || showEvolveAction || showDeadAction) && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '6px', marginTop: '10px', borderTop: '1px solid #2e2f3a', paddingTop: '8px' }}>
              {showReviveAction ? (
                <button
                  onClick={() => onRevive(pokemon)}
                  style={{ gridColumn: '1 / -1', minWidth: 0, padding: '3px 6px', fontSize: '0.75em', cursor: 'pointer', color: '#7ec8e3', borderColor: '#7ec8e3', borderRadius: '6px' }}
                >Revive</button>
              ) : (
                <>
                  {showPartyAction ? (
                    inParty ? (
                      <button
                        onClick={() => onRemoveFromParty(pokemon)}
                        style={{ minWidth: 0, padding: '3px 6px', fontSize: '0.75em', cursor: 'pointer', color: '#e55', borderColor: '#e55', borderRadius: '6px' }}
                      >- Party</button>
                    ) : (
                      <button
                        onClick={() => onAddToParty(pokemon)}
                        style={{ minWidth: 0, padding: '3px 6px', fontSize: '0.75em', cursor: 'pointer', color: '#5ba85b', borderColor: '#5ba85b', borderRadius: '6px' }}
                      >+ Party</button>
                    )
                  ) : <span />}
                  {showEvolveAction ? (
                    <button
                      onClick={() => onEvolve(pokemon)}
                      style={{ minWidth: 0, padding: '3px 6px', fontSize: '0.75em', cursor: 'pointer', color: '#7ec8e3', borderColor: '#7ec8e3', borderRadius: '6px' }}
                    >Evolve</button>
                  ) : <span />}
                  {showDeadAction ? (
                    <button
                      onClick={() => onDead(pokemon)}
                      style={{ minWidth: 0, padding: '3px 6px', fontSize: '0.75em', cursor: 'pointer', color: '#e55', borderColor: '#e55', borderRadius: '6px' }}
                    >✕ Dead</button>
                  ) : <span />}
                </>
              )}
            </div>
          )}

          {location_name && (
            <div style={{ paddingTop: '8px', borderTop: '1px solid #2e2f3a', fontSize: '0.65em', color: '#666', textAlign: 'center', fontStyle: 'italic' }}>
              Met at {location_name}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default PokemonCard
