import { useState, useEffect } from 'react'
import { apiFetch } from '../utils/api'
import { isLocalRun } from '../utils/dataLayer'
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

const CARD_ACTION_BUTTON_STYLE = {
  minHeight: '26px',
  minWidth: 0,
  padding: '3px 6px',
  border: '1px solid var(--border-strong)',
  borderRadius: '10px',
  background: 'var(--surface-deep)',
  color: 'var(--text-secondary)',
  cursor: 'pointer',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  font: 'inherit',
  fontSize: '0.68em',
  lineHeight: 1,
  whiteSpace: 'nowrap',
}

function PokemonCard({ pokemon, inParty = false, onAddToParty, onRemoveFromParty, onDead, onRevive, onEvolve, runId, attemptId }) {
  const { species_name, nickname, nature, status, shiny, level_met, location_name,
          type1, type2, hp, atk, def, spa, spd, spe, bst } = pokemon
  const displayName = nickname || species_name || '???'
  const hasStats = hp != null

  const statusInfo = STATUS_STYLE[status] || { color: '#aaa', label: status }
  const badgeIds = parseBadgeIds(pokemon.badges_earned)
  const localRun = Boolean(runId) && isLocalRun(runId)
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

    apiFetch(`/api/badges?ids=${badgeIds.join(',')}`)
      .then(res => res.json())
      .then(data => setBadgeMeta(Array.isArray(data) ? data : []))
      .catch(() => setBadgeMeta([]))
  }, [pokemon.pokemon_id, badgeIds.join(','), localRun])

  const badgeById = new Map(badgeMeta.map(b => [b.badge_id, b]))

  // Fetch trainer/badge data when dropdown opens
  useEffect(() => {
    if (!showDropdown || !runId || !attemptId || !pokemon.pokemon_id) {
      return
    }

    if (localRun) {
      setTrainerData({
        trainers_defeated_count: Number(pokemon.trainers_defeated_count || pokemon.trainers_defeated || 0),
        bosses_defeated_count: Number(pokemon.bosses_defeated_count || 0),
        rivals_defeated_count: Number(pokemon.rivals_defeated_count || 0),
        badges_earned: badgeIds.map(badgeId => ({
          badge_id: badgeId,
          badge_name: badgeMeta.find(badge => Number(badge.badge_id) === badgeId)?.badge_name || `Badge ${badgeId}`,
        })),
      })
      setLoading(false)
      return
    }

    setLoading(true)
    apiFetch(`/api/pokemon/${pokemon.pokemon_id}/trainers-badges/${runId}/${attemptId}`)
      .then(res => res.json())
      .then(data => {
        setTrainerData(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch trainer/badge data:', err)
        setLoading(false)
      })
  }, [showDropdown, runId, attemptId, pokemon.pokemon_id, localRun, badgeIds.join(','), badgeMeta])

  return (
    <div style={{
      background: 'var(--surface)', border: inParty ? '1px solid #5ba85b' : '1px solid var(--border-strong)', borderRadius: '8px',
      overflow: 'hidden', width: '220px', minWidth: '220px', maxWidth: '220px', boxSizing: 'border-box',
      boxShadow: '0 2px 6px rgba(0,0,0,0.4)',
      opacity: status === 'Dead' ? 0.65 : 1,
      display: 'flex', flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '10px',
        padding: '8px 10px', background: 'var(--surface-mid)', borderBottom: '1px solid var(--border)'
      }}>
        {/* Sprite */}
        <div style={{ flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '3px' }}>
          <Sprite speciesId={pokemon.species_id} size={48} shiny={shiny === 'True' || shiny === true} />
          {bst != null && (
            <div style={{ fontSize: '0.6em', color: 'var(--text-secondary)' }}>BST {bst}</div>
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
            {pokemon.gender === 'female'
              ? <span title="Female" style={{ fontSize: '0.85em', color: '#e84d8a', flexShrink: 0 }}>♀</span>
              : pokemon.gender === 'male'
              ? <span title="Male" style={{ fontSize: '0.85em', color: '#4d8fe8', flexShrink: 0 }}>♂</span>
              : null}
          </div>
          <div style={{ fontSize: '0.75em', color: 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {species_name || '—'}
          </div>
          <TypeIconRow types={[type1, type2]} height={15} gap={4} style={{ marginTop: '3px' }} />
        </div>
      </div>

      {/* Body */}
      <div style={{ padding: '8px 10px', flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Meta row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', fontSize: '0.72em', color: 'var(--text-secondary)' }}>
          <span style={{ color: statusInfo.color, fontWeight: 'bold' }}>{statusInfo.label}</span>
          <span style={{ color: 'var(--text-primary)' }}>{nature || '—'}</span>
          {level_met != null && <span>Lv. {level_met}</span>}
        </div>

        <div style={{ marginBottom: '8px', borderTop: '1px solid var(--border)', paddingTop: '6px', minHeight: '30px', boxSizing: 'border-box' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', minHeight: '18px', alignItems: 'center' }}>
            {badgeIds.map(badgeId => (
              <img
                key={badgeId}
                src={`/sprites/Badges/${badgeId}.png`}
                alt={badgeById.get(badgeId)?.badge_name || `Badge ${badgeId}`}
                title={badgeById.get(badgeId)?.badge_name || `Badge ${badgeId}`}
                loading="lazy"
                decoding="async"
                style={{ width: '18px', height: '18px', imageRendering: 'pixelated' }}
              />
            ))}
          </div>
        </div>

        {/* Battle Stats Dropdown */}
        {runId && attemptId && (
          <div style={{ marginBottom: '8px', borderTop: '1px solid var(--border)', paddingTop: '6px' }}>
            <button
              type="button"
              onClick={() => setShowDropdown(!showDropdown)}
              style={{
                width: '100%',
                minHeight: '30px',
                padding: '4px 8px',
                fontSize: '0.72em',
                color: '#7ec8e3',
                border: '1px solid #7ec8e3',
                borderRadius: '999px',
                background: 'rgba(126,200,227,0.12)',
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
              <div style={{ marginTop: '6px', fontSize: '0.68em', color: 'var(--text-secondary)', paddingLeft: '12px' }}>
                {loading ? (
                  <div>Loading...</div>
                ) : trainerData ? (
                  <div style={{ display: 'grid', gap: '6px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '3px' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>trainers</span>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>{trainerData.trainers_defeated_count ?? trainerData.trainers_defeated ?? 0}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '3px' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>bosses</span>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>{trainerData.bosses_defeated_count ?? 0}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '3px' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>rivals</span>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>{trainerData.rivals_defeated_count ?? 0}</span>
                    </div>

                    <div style={{ marginTop: '2px', color: 'var(--text-secondary)' }}>badges</div>
                    {trainerData.badges_earned?.length > 0 ? (
                      <div style={{ display: 'grid', gap: '4px' }}>
                        {trainerData.badges_earned.map(badge => (
                          <div key={badge.badge_id} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '3px', gap: '8px' }}>
                            <span style={{ color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {(badge.badge_name || `Badge ${badge.badge_id}`).toLowerCase()}
                            </span>
                            <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic', flexShrink: 0 }}>
                              {(badge.trainer_name || 'Leader').toLowerCase()}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ color: 'var(--text-secondary)' }}>none</div>
                    )}
                  </div>
                ) : (
                  <div style={{ color: 'var(--text-secondary)' }}>No battle stats yet</div>
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
              trackColor="var(--surface-deep)"
              reserveModifierSpace={false}
              showNatureModifierText={false}
              colorNatureModifiedLabel
            />
          ) : (
            <div style={{ fontSize: '0.75em', color: 'var(--text-secondary)', textAlign: 'center', padding: '8px 0' }}>
              No stat data
            </div>
          )
        )}

        <div style={{ marginTop: 'auto' }}>
          {(showReviveAction || showPartyAction || showEvolveAction || showDeadAction) && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '4px', marginTop: '10px', borderTop: '1px solid var(--border)', paddingTop: '8px' }}>
              {showReviveAction ? (
                <button
                  type="button"
                  onClick={() => onRevive(pokemon)}
                  style={{ ...CARD_ACTION_BUTTON_STYLE, gridColumn: '1 / -1', color: '#7ec8e3', borderColor: '#7ec8e3', background: 'rgba(126,200,227,0.12)' }}
                >Revive</button>
              ) : (
                <>
                  {showPartyAction ? (
                    inParty ? (
                      <button
                        type="button"
                        onClick={() => onRemoveFromParty(pokemon)}
                        style={{ ...CARD_ACTION_BUTTON_STYLE, color: '#e55', borderColor: '#e55', background: 'rgba(224,82,82,0.12)' }}
                      >Party -</button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => onAddToParty(pokemon)}
                        style={{ ...CARD_ACTION_BUTTON_STYLE, color: '#5ba85b', borderColor: '#5ba85b', background: 'rgba(91,168,91,0.12)' }}
                      >Party +</button>
                    )
                  ) : <span />}
                  {showEvolveAction ? (
                    <button
                      type="button"
                      onClick={() => onEvolve(pokemon)}
                      style={{ ...CARD_ACTION_BUTTON_STYLE, color: 'var(--accent)', borderColor: 'var(--accent-border)', background: 'var(--accent-bg)' }}
                    >Evolve</button>
                  ) : <span />}
                  {showDeadAction ? (
                    <button
                      type="button"
                      onClick={() => onDead(pokemon)}
                      style={{ ...CARD_ACTION_BUTTON_STYLE, color: '#e55', borderColor: '#e55', background: 'rgba(224,82,82,0.12)' }}
                    >Dead</button>
                  ) : <span />}
                </>
              )}
            </div>
          )}

          {location_name && (
            <div style={{ paddingTop: '8px', borderTop: '1px solid var(--border)', fontSize: '0.65em', color: 'var(--text-secondary)', textAlign: 'center', fontStyle: 'italic' }}>
              Met at {location_name}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default PokemonCard
