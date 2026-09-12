import { useState, useEffect, useMemo } from 'react'
import { apiFetch } from '../utils/api'
import { getSpeciesLearnset, isLocalRun } from '../utils/dataLayer'
import { formatConstant, parseBadgeIds, IV_STAT_KEYS, hasAnyIv } from '../utils/pokemonFormat'
import Sprite from './Sprite'
import TypeIcon, { TypeIconRow } from './TypeIcon'
import PokemonStatRows, { POKEMON_STAT_ROWS } from './PokemonStatRows'

const STATUS_STYLE = {
  Captured: { color: '#5ba85b', label: 'Alive' },
  Dead: { color: '#e55', label: 'Fallen' },
}

function Section({ title, aside = null, children }) {
  return (
    <section className="pokemon-summary__section">
      <div className="pokemon-summary__section-head">
        <span>{title}</span>
        {aside}
      </div>
      {children}
    </section>
  )
}

/**
 * The in-game "Summary" screen for one caught Pokemon: identity, abilities,
 * stats, the level-up learnset for the run's game, its battle record, and
 * the run actions (party, evolve, fallen / revive). Reference data that the
 * box row does not carry (the learnset, the badge names, the trainer
 * counts) is fetched when the panel opens for that Pokemon.
 *
 * Fetched results are stored with the key they were fetched for, and a
 * result is only used while its key still matches; that way a species or
 * Pokemon change shows the loading state without an effect having to
 * reset anything. Mount one instance per Pokemon (key on pokemon_id).
 */
function PokemonSummary({
  pokemon,
  gameId = null,
  runId,
  attemptId,
  inParty = false,
  canEvolve = false,
  onAddToParty,
  onRemoveFromParty,
  onEvolve,
  onDead,
  onRevive,
  onClose,
}) {
  const {
    pokemon_id, species_id, species_name, nickname, nature, status, shiny, gender,
    level_met, location_name, type1, type2, bst, hp,
  } = pokemon
  const isShiny = shiny === 'True' || shiny === true
  const fallen = status === 'Dead'
  const displayName = nickname || species_name || '???'
  const statusInfo = STATUS_STYLE[status] || { color: 'var(--text-secondary)', label: status }
  const localRun = Boolean(runId) && isLocalRun(runId)
  const badgeIds = useMemo(() => parseBadgeIds(pokemon.badges_earned), [pokemon.badges_earned])
  const badgeKey = badgeIds.join(',')

  const chosenAbility = formatConstant(pokemon.ability)
  const abilityOptions = [
    { name: formatConstant(pokemon.ability1), hidden: false },
    { name: formatConstant(pokemon.ability2), hidden: false },
    { name: formatConstant(pokemon.ability3), hidden: true },
  ].filter((option, index, all) => option.name && all.findIndex(o => o.name === option.name) === index)

  const [confirmDead, setConfirmDead] = useState(false)

  // Learnset, keyed by species + game.
  const learnsetKey = `${species_id}:${gameId ?? ''}`
  const [learnsetResult, setLearnsetResult] = useState(null)
  useEffect(() => {
    let cancelled = false
    getSpeciesLearnset(species_id, gameId)
      .then(data => { if (!cancelled) setLearnsetResult({ key: learnsetKey, data }) })
      .catch(() => { if (!cancelled) setLearnsetResult({ key: learnsetKey, data: { version_group_id: null, moves: [] } }) })
    return () => { cancelled = true }
  }, [species_id, gameId, learnsetKey])
  const learnset = learnsetResult?.key === learnsetKey ? learnsetResult.data : null

  // Badge names for the ids on the row (guest runs only carry the ids).
  const [badgeMetaResult, setBadgeMetaResult] = useState(null)
  useEffect(() => {
    if (!badgeKey) return
    let cancelled = false
    apiFetch(`/api/badges?ids=${badgeKey}`)
      .then(res => res.json())
      .then(data => { if (!cancelled) setBadgeMetaResult({ key: badgeKey, data: Array.isArray(data) ? data : [] }) })
      .catch(() => { if (!cancelled) setBadgeMetaResult({ key: badgeKey, data: [] }) })
    return () => { cancelled = true }
  }, [badgeKey])
  const badgeMeta = useMemo(
    () => (badgeKey && badgeMetaResult?.key === badgeKey ? badgeMetaResult.data : []),
    [badgeKey, badgeMetaResult],
  )
  const badgeById = useMemo(() => new Map(badgeMeta.map(b => [Number(b.badge_id), b])), [badgeMeta])

  // Battle record: counted on the row for guest runs, fetched for API runs.
  const localRecord = useMemo(() => {
    if (!localRun) return null
    return {
      trainers_defeated_count: Number(pokemon.trainers_defeated_count || pokemon.trainers_defeated || 0),
      bosses_defeated_count: Number(pokemon.bosses_defeated_count || 0),
      rivals_defeated_count: Number(pokemon.rivals_defeated_count || 0),
      badges_earned: badgeIds.map(badgeId => ({
        badge_id: badgeId,
        badge_name: badgeById.get(badgeId)?.badge_name || `Badge ${badgeId}`,
      })),
    }
  }, [localRun, pokemon, badgeIds, badgeById])

  const recordKey = `${pokemon_id}:${runId}:${attemptId}`
  const [recordResult, setRecordResult] = useState(null)
  useEffect(() => {
    if (localRun || !runId || !attemptId || !pokemon_id) return
    let cancelled = false
    apiFetch(`/api/pokemon/${pokemon_id}/trainers-badges/${runId}/${attemptId}`)
      .then(res => res.json())
      .then(data => { if (!cancelled) setRecordResult({ key: recordKey, data }) })
      .catch(err => {
        console.error('Failed to fetch battle record:', err)
        if (!cancelled) setRecordResult({ key: recordKey, data: {} })
      })
    return () => { cancelled = true }
  }, [localRun, pokemon_id, runId, attemptId, recordKey])
  const record = localRun ? localRecord : (recordResult?.key === recordKey ? recordResult.data : null)

  const moves = learnset?.moves || []

  return (
    <div className="pokemon-summary" data-status={status}>
      <div className="pokemon-summary__header">
        <Sprite speciesId={species_id} size={96} shiny={isShiny} female={gender === 'female'} />
        <div className="pokemon-summary__identity">
          <div className="pokemon-summary__name">
            {displayName}
            {isShiny && <span title="Shiny" className="pokemon-summary__shiny">★</span>}
            {gender === 'female' && <span title="Female" style={{ color: '#e84d8a' }}>♀</span>}
            {gender === 'male' && <span title="Male" style={{ color: '#4d8fe8' }}>♂</span>}
          </div>
          {nickname && <div className="pokemon-summary__species">{species_name}</div>}
          <TypeIconRow types={[type1, type2]} height={18} gap={5} style={{ marginTop: '4px' }} />
          <div className="pokemon-summary__status" style={{ color: statusInfo.color }}>{statusInfo.label}</div>
        </div>
        {onClose && (
          <button type="button" className="pokemon-summary__close" onClick={onClose} aria-label="Close summary">✕</button>
        )}
      </div>

      <dl className="pokemon-summary__facts">
        <div><dt>Nature</dt><dd>{nature || '—'}</dd></div>
        <div><dt>Ability</dt><dd>{chosenAbility || '—'}</dd></div>
        <div><dt>Met at</dt><dd>{location_name || '—'}</dd></div>
        <div><dt>Level met</dt><dd>{level_met != null ? level_met : '—'}</dd></div>
      </dl>

      {abilityOptions.length > 0 && (
        <Section title="Abilities">
          <div className="pokemon-summary__abilities">
            {abilityOptions.map(option => (
              <span
                key={option.name}
                className={`pokemon-summary__ability${option.name === chosenAbility ? ' pokemon-summary__ability--chosen' : ''}`}
              >
                {option.name}
                {option.hidden && <span className="pokemon-summary__ability-tag">hidden</span>}
              </span>
            ))}
          </div>
        </Section>
      )}

      <Section title="Stats" aside={<span className="pokemon-summary__bst">BST {bst ?? '—'}</span>}>
        {hp != null ? (
          <PokemonStatRows
            stats={pokemon}
            nature={nature}
            rowGap="5px"
            columnGap="6px"
            labelColumnWidth={70}
            labelTextWidth={28}
            modifierWidth={36}
            valueColumnWidth={28}
            barHeight={8}
            labelFontSize="0.72em"
            valueFontSize="0.78em"
            trackColor="var(--surface-deep)"
            colorNatureModifiedLabel
          />
        ) : (
          <div className="pokemon-summary__empty">No stat data for this species.</div>
        )}
        {hasAnyIv(pokemon.ivs) && (
          <div className="pokemon-summary__ivs" title="Individual values">
            <span className="pokemon-summary__ivs-label">IVs</span>
            {IV_STAT_KEYS.map((key, index) => (
              <span key={key} className="pokemon-summary__iv">
                <span>{POKEMON_STAT_ROWS[index].label}</span>
                <strong>{pokemon.ivs[key] ?? '—'}</strong>
              </span>
            ))}
          </div>
        )}
      </Section>

      <Section title="Level-up moves">
        {learnset === null ? (
          <div className="pokemon-summary__empty">Loading moves…</div>
        ) : moves.length === 0 ? (
          <div className="pokemon-summary__empty">No learnset data for this species.</div>
        ) : (
          <div className="pokemon-summary__moves-scroll">
            <table className="pokemon-summary__moves">
              <thead>
                <tr><th>Lv</th><th>Move</th><th>Type</th><th>Cat</th><th>Pow</th><th>Acc</th></tr>
              </thead>
              <tbody>
                {moves.map(move => {
                  const known = level_met != null && move.learn_level <= level_met
                  return (
                    <tr key={`${move.learn_level}-${move.move_id}`} className={known ? 'pokemon-summary__move--known' : ''}>
                      <td className="pokemon-summary__move-level">{move.learn_level === 0 ? 'Evo' : move.learn_level}</td>
                      <td className="pokemon-summary__move-name">{move.move_name}</td>
                      <td>{move.type && <TypeIcon type={move.type} height={14} />}</td>
                      <td>
                        <img
                          src={`/sprites/types/${(move.damage_class || 'status').toLowerCase()}.png`}
                          alt={move.damage_class || 'Status'}
                          title={move.damage_class || 'Status'}
                          style={{ height: '16px', width: 'auto' }}
                        />
                      </td>
                      <td>{move.power ?? '—'}</td>
                      <td>{move.accuracy ?? '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section title="Battle record">
        {record === null ? (
          <div className="pokemon-summary__empty">Loading…</div>
        ) : (
          <>
            <div className="pokemon-summary__record">
              <div><span>Trainers</span><strong>{record.trainers_defeated_count ?? record.trainers_defeated ?? 0}</strong></div>
              <div><span>Bosses</span><strong>{record.bosses_defeated_count ?? 0}</strong></div>
              <div><span>Rivals</span><strong>{record.rivals_defeated_count ?? 0}</strong></div>
            </div>
            <div className="pokemon-summary__badges">
              {(record.badges_earned || []).length === 0 ? (
                <span className="pokemon-summary__empty">No badges yet</span>
              ) : record.badges_earned.map(badge => (
                <span key={badge.badge_id} className="pokemon-summary__badge" title={badge.trainer_name || ''}>
                  <img
                    src={`/sprites/Badges/${badge.badge_id}.png`}
                    alt=""
                    loading="lazy"
                    style={{ width: '18px', height: '18px', imageRendering: 'pixelated' }}
                  />
                  {badge.badge_name || badgeById.get(Number(badge.badge_id))?.badge_name || `Badge ${badge.badge_id}`}
                </span>
              ))}
            </div>
          </>
        )}
      </Section>

      <div className="pokemon-summary__actions">
        {fallen ? (
          onRevive && (
            <button type="button" className="pokemon-summary__action pokemon-summary__action--revive" onClick={() => onRevive(pokemon)}>
              Revive
            </button>
          )
        ) : (
          <>
            {inParty
              ? onRemoveFromParty && (
                <button type="button" className="pokemon-summary__action pokemon-summary__action--remove" onClick={() => onRemoveFromParty(pokemon)}>
                  Party −
                </button>
              )
              : onAddToParty && (
                <button type="button" className="pokemon-summary__action pokemon-summary__action--add" onClick={() => onAddToParty(pokemon)}>
                  Party +
                </button>
              )}
            {canEvolve && onEvolve && (
              <button type="button" className="pokemon-summary__action pokemon-summary__action--evolve" onClick={() => onEvolve(pokemon)}>
                Evolve
              </button>
            )}
            {onDead && (
              confirmDead ? (
                <>
                  <button type="button" className="pokemon-summary__action pokemon-summary__action--dead" onClick={() => { setConfirmDead(false); onDead(pokemon) }}>
                    Confirm fallen
                  </button>
                  <button type="button" className="pokemon-summary__action" onClick={() => setConfirmDead(false)}>
                    Cancel
                  </button>
                </>
              ) : (
                <button type="button" className="pokemon-summary__action pokemon-summary__action--dead" onClick={() => setConfirmDead(true)}>
                  Fallen
                </button>
              )
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default PokemonSummary
