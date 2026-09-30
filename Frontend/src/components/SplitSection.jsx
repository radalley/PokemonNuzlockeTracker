import { useState } from 'react'
import Sprite from './Sprite'
import { Button } from './Button'
import MethodIcon from './MethodIcon'
import BattleFormatPill from './BattleFormatPill'
import { typeBadgeStyle } from './typeColors'
import { SplitItemEditor, SplitItems } from './SplitItems'
import { itemSummary, titleCase } from '../utils/splitItems'
import { methodMeta } from '../utils/encounterTables'
import { formatTrainerClass, splitInitial, splitPhrase } from '../utils/splitFeed'

function ReturnArrow() {
  return <svg className="split-returns__arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M7 17L17 7" /><path d="M8 7h9v9" /></svg>
}

function ReturnsIcon() {
  return <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M9 14L4 9l5-5" /><path d="M4 9h11a5 5 0 0 1 0 10h-3" /></svg>
}

/**
 * One split of the attempt page: its chapter band, the items curated for
 * it, the "New encounters / New trainers" jump lists (content that opened
 * in earlier areas), then its own rows in story order with the leader last.
 */
export default function SplitSection({
  section, total, gameId, items = [], record = null, encounterMethods = [],
  editMode = false, gymSplits = [], expanded, onToggle, onJump, renderRow, onItemsChanged = null,
}) {
  const [editor, setEditor] = useState(null)
  const { split, state, color, rows, leaderRow, newEncounters, newTrainers } = section
  const isGym = split.kind === 'gym'
  const ordinalLabel = split.kind === 'league' ? 'League' : split.kind === 'postgame' ? 'Postgame' : `Split ${section.ordinal + 1} of ${total}`
  const stateLabel = state === 'done' ? 'beaten' : state === 'current' ? 'current' : 'upcoming'
  const locationRows = rows.filter(row => row.event_type === 'Location')
  const trainerTotal = locationRows.reduce((sum, row) => sum + (Number(row.trainer_count) || 0), 0)
  const trainerBeaten = locationRows.reduce((sum, row) => sum + Math.max(0, (Number(row.trainer_count) || 0) - (Number(row.available_trainer_count) || 0)), 0)
  const newAreaCount = locationRows.filter(row => !row.is_bonus_location).length
  const returnCount = new Set([...newEncounters, ...newTrainers].map(entry => entry.encounterKey)).size
  const anchor = `section-${split.split_key}`
  const collapsed = !expanded

  const openEditor = item => setEditor(item ? { ...item } : { split_key: split.split_key, item_name: '', method: '' })

  return (
    <section id={anchor} className={`split-section split-section--${state}`} style={{ '--split-color': color }} aria-label={`${split.label}, ${stateLabel}`}>
      <button type="button" className={`split-band${collapsed ? ' split-band--collapsed' : ''}`} aria-expanded={expanded} onClick={onToggle}>
        <span className="split-band__medal" aria-hidden="true">
          {state === 'done'
            ? <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12l5 5 9-10" /></svg>
            : splitInitial(split)}
        </span>
        <span style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <span className="split-band__kicker">{ordinalLabel} · {stateLabel}</span>
          <span className="split-band__name">{split.label}</span>
          {!collapsed && (
            <span className="split-band__meta">
              {split.type_focus && <span className="type-chip" style={typeBadgeStyle(split.type_focus)}>{String(split.type_focus).toUpperCase()}</span>}
              {isGym && split.title && <span>{split.title}</span>}
              {split.level_cap != null && <><span>·</span><span>Level cap {split.level_cap}</span></>}
              {split.battle_type && split.battle_type !== 'single' && <><span>·</span><BattleFormatPill format={split.battle_type} fontSize="0.78em" /></>}
            </span>
          )}
          {collapsed && (
            <span className="split-band__meta" style={{ fontSize: '0.78em', color: 'var(--text-secondary)' }}>
              {[split.type_focus, split.level_cap != null ? `cap ${split.level_cap}` : null, `${newAreaCount} areas`].filter(Boolean).join(' · ')}
            </span>
          )}
        </span>
        <span className="split-band__side">
          {record?.party?.length > 0 && (
            <span className="split-band__party" aria-label="Party that beat this split">
              {record.party.map(member => (
                <span key={member.slot} className={member.died_in_battle ? 'fallen' : undefined} title={`${member.nickname || member.species_name || 'Pokémon'}${member.died_in_battle ? ' · fell in this battle' : ''}`}>
                  <Sprite speciesId={member.species_id} shiny={member.shiny === true || member.shiny === 'True'} female={member.gender?.toLowerCase() === 'female'} size={30} useIcon alt={member.nickname || member.species_name || ''} />
                </span>
              ))}
            </span>
          )}
          {!collapsed && <span>{newAreaCount} new area{newAreaCount === 1 ? '' : 's'}{returnCount ? ` · ${returnCount} return${returnCount === 1 ? '' : 's'}` : ''}</span>}
          {!collapsed && trainerTotal > 0 && <span><b>{trainerBeaten} / {trainerTotal}</b> trainers</span>}
          <span className="split-band__chev" aria-hidden="true">{collapsed ? 'Expand ▾' : '▴'}</span>
        </span>
      </button>

      {expanded && (
        <div className="split-section__body">
          {isGym && (
            <details className="split-items">
              <summary>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M20 12v8H4v-8" /><path d="M2 7h20v5H2z" /><path d="M12 22V7" /></svg>
                <b>Items this split</b>
                <span>{itemSummary(items)}</span>
              </summary>
              <div className="split-items__body">
                {editMode && !editor && <div style={{ marginBottom: '8px' }}><Button size="sm" tone="success" onClick={() => openEditor(null)}>+ Add item</Button></div>}
                {editMode && editor && <SplitItemEditor gameId={gameId} editor={editor} setEditor={setEditor} splits={gymSplits} splitLabel={s => s.label} onSaved={onItemsChanged} onRemoved={onItemsChanged} />}
                <SplitItems items={items} name={split.label} editMode={editMode} openEditor={openEditor} />
              </div>
            </details>
          )}

          {(newEncounters.length > 0 || newTrainers.length > 0) && (
            <>
              <div className="split-section__label split-section__label--returns"><ReturnsIcon />Opened up in earlier areas</div>
              <div className="split-returns">
                {newEncounters.length > 0 && (
                  <div className="split-returns__list" aria-label="New encounters in earlier areas">
                    <div className="split-returns__head"><b>New encounters</b><small>{newEncounters.length} area{newEncounters.length === 1 ? '' : 's'}</small></div>
                    {newEncounters.map(entry => (
                      <button
                        key={entry.encounterKey}
                        type="button"
                        className={`split-returns__entry ${entry.encounterUsed ? 'split-returns__entry--muted' : 'split-returns__entry--open'}`}
                        onClick={() => onJump(entry, 'encounter')}
                        title={`Open ${entry.name} in ${splitPhrase(entry.homeSplit)}`}
                      >
                        <span className="split-returns__body">
                          <span className="split-returns__title">
                            <b>{entry.name}</b>
                            <small className={entry.encounterUsed ? '' : 'open'}>{entry.encounterUsed ? `Used${entry.encounterName ? ` · ${titleCase(entry.encounterName)}` : ''}` : 'Encounter still open'}</small>
                          </span>
                          <span className="split-returns__chips">
                            {entry.areas.map(area => <span key={`area-${area}`} className="method-chip">{area}</span>)}
                            {entry.methods.map(m => {
                              const meta = methodMeta(encounterMethods, m.method)
                              return (
                                <span key={m.method} className="method-chip">
                                  <MethodIcon group={meta.group} rare={Boolean(meta.is_rare)} size={14} title={meta.label} />
                                  {meta.label}
                                  {m.rare.map(r => <span key={r.species_id} className="rare">· {titleCase(r.name)}{r.rate != null ? ` ${r.rate}%` : ''}</span>)}
                                </span>
                              )
                            })}
                          </span>
                        </span>
                        <ReturnArrow />
                      </button>
                    ))}
                  </div>
                )}
                {newTrainers.length > 0 && (
                  <div className="split-returns__list" aria-label="New trainers in earlier areas">
                    <div className="split-returns__head"><b>New trainers</b><small>{newTrainers.length} area{newTrainers.length === 1 ? '' : 's'} · {newTrainers.reduce((n, e) => n + e.beaten, 0)} / {newTrainers.reduce((n, e) => n + e.trainers.length, 0)}</small></div>
                    {newTrainers.map(entry => (
                      <button
                        key={entry.encounterKey}
                        type="button"
                        className={`split-returns__entry${entry.beaten === entry.trainers.length ? ' split-returns__entry--muted' : ''}`}
                        onClick={() => onJump(entry, 'trainers')}
                        title={`Open ${entry.name}'s trainers in ${splitPhrase(entry.homeSplit)}`}
                      >
                        <span className="split-returns__body">
                          <span className="split-returns__title"><b>{entry.name}</b><small>{entry.beaten} / {entry.trainers.length} beaten</small></span>
                          <span className="split-returns__chips">
                            {entry.trainers.map(t => {
                              const cls = formatTrainerClass(t.trainer_class)
                              const name = titleCase(t.trainer_name)
                              const label = name && name.toLowerCase() !== cls.toLowerCase() ? `${cls} ${name}` : cls || name
                              return (
                                <span key={t.trainer_id} className={`trainer-chip${t.is_defeated ? ' trainer-chip--beaten' : ''}`}>
                                  <svg width="12" height="14" viewBox="0 0 44 58" aria-hidden="true"><circle cx="22" cy="15" r="10" fill="currentColor" opacity="0.6" /><path d="M5 56c0-13 8-24 17-24s17 11 17 24z" fill="currentColor" opacity="0.6" /></svg>
                                  {label}{t.max_level != null ? ` · Lv ${t.max_level}` : ''}
                                </span>
                              )
                            })}
                          </span>
                        </span>
                        <ReturnArrow />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

          {rows.length > 0 && <div className="split-section__label">{newAreaCount > 0 ? 'New areas' : 'This split'}</div>}
          {rows.map(row => (
            row === leaderRow
              ? <div key="leader"><div className="split-section__label">{isGym ? 'Leader' : 'Final battle'}</div>{renderRow(row)}</div>
              : renderRow(row)
          ))}
        </div>
      )}
    </section>
  )
}
