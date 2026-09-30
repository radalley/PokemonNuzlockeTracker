import { useEffect, useRef, useState } from 'react'
import Sprite from './Sprite'
import MethodIcon from './MethodIcon'
import { GROUP_HUES, SEASONS, conditionLabel, conditionSeasons, seasonLabel, slotKey, visibleOverlays, visibleTables } from '../utils/encounterTables'
import { splitInitial } from '../utils/splitFeed'

// The blank-encounter view: a location's wild tables, one method at a
// time (tabs), split by area and season, with the location's legendaries
// and statics in a strip on top. A tap only SELECTS a species; LocationRow
// owns the selection and the Caught / Missed confirmation.

// Theme tokens (index.css): readable as text on light and dark surfaces.
const GOLD = 'var(--rare)'
const ACTIVE = 'var(--pick)'
const DUPE_OPACITY = 0.35

const PILL_STYLE = {
  font: 'inherit',
  fontSize: '0.78em',
  padding: '5px 11px',
  borderRadius: '999px',
  border: '1px solid var(--border-strong)',
  background: 'var(--surface-deep)',
  color: 'var(--text-secondary)',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
}

function levelText(row) {
  if (row.min_level == null) return null
  const max = row.max_level == null ? row.min_level : row.max_level
  return max === row.min_level ? `Lv ${row.min_level}` : `Lv ${row.min_level}–${max}`
}

function Tag({ children, color = 'var(--text-secondary)', title }) {
  return (
    <span title={title} style={{ fontSize: '0.72em', padding: '1px 7px', borderRadius: '999px', border: `1px solid ${color}`, color, whiteSpace: 'nowrap', flexShrink: 0 }}>
      {children}
    </span>
  )
}

function OddsRow({ row, hue, dupe, disabled, highlighted, selected, onSelect, overlay = false, tableCondition = null }) {
  const buttonRef = useRef(null)
  const rate = row.rate == null || row.rate === '' ? NaN : Number(row.rate)
  const level = levelText(row)
  // An overlay limited to fewer seasons than its table says which ones;
  // the tab already names the table's own season.
  const ownSeason = overlay && Boolean(row.condition)
    && conditionSeasons(row.condition).length < conditionSeasons(tableCondition).length
  const hasTags = Boolean((overlay && row.tag) || level || ownSeason || dupe)
  const edge = selected ? ACTIVE : highlighted ? GOLD : 'transparent'
  // A jump from the rare strip lands here: bring the row on screen.
  useEffect(() => {
    if (!highlighted) return
    const reduce = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    buttonRef.current?.scrollIntoView?.({ block: 'center', behavior: reduce ? 'auto' : 'smooth' })
  }, [highlighted])
  return (
    <button
      ref={buttonRef}
      type="button"
      className={`encounter-tables__row${overlay ? ' encounter-tables__row--overlay' : ''}${dupe ? ' encounter-tables__row--dupe' : ''}${selected ? ' encounter-tables__row--selected' : ''}`}
      disabled={disabled}
      aria-pressed={selected}
      onClick={() => onSelect(row)}
      title={row.note || undefined}
      style={{
        display: 'grid',
        // Tags (Legendary, Lv, season, Dupe) take a second line under the
        // name, so they never squeeze the name or widen the row.
        gridTemplateColumns: '28px minmax(0, 1fr) 56px 42px',
        alignItems: 'center',
        columnGap: '8px',
        rowGap: '3px',
        width: '100%',
        minWidth: 0,
        minHeight: '40px',
        padding: '4px 8px',
        border: `1px solid ${edge}`,
        borderRadius: '8px',
        boxShadow: selected ? `inset 3px 0 0 ${ACTIVE}` : overlay ? `inset 3px 0 0 ${GOLD}` : 'none',
        background: selected ? 'color-mix(in srgb, var(--pick) 14%, transparent)' : highlighted ? 'color-mix(in srgb, var(--rare) 12%, transparent)' : 'transparent',
        color: 'var(--text-primary)',
        font: 'inherit',
        textAlign: 'left',
        cursor: disabled ? 'not-allowed' : 'pointer',
        // a selected dupe stays readable so the player sees what they picked
        opacity: dupe && !selected ? DUPE_OPACITY : 1,
      }}
    >
      <Sprite speciesId={row.species_id} size={28} useIcon style={hasTags ? { gridRow: '1 / span 2' } : undefined} />
      <span className="encounter-tables__name" style={{ fontSize: '0.86em', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{row.name}</span>
      <span aria-hidden="true" style={{ height: '6px', borderRadius: '999px', background: 'var(--surface-deep)', overflow: 'hidden' }}>
        <span style={{ display: 'block', height: '100%', width: `${Math.max(0, Math.min(100, Number.isFinite(rate) ? rate : 0))}%`, background: overlay ? GOLD : hue, borderRadius: '999px' }} />
      </span>
      <span className="encounter-tables__rate" style={{ fontSize: '0.82em', textAlign: 'right', fontVariantNumeric: 'tabular-nums', color: overlay ? GOLD : 'var(--text-primary)' }}>
        {Number.isFinite(rate) ? `${rate}%` : '—'}
      </span>
      {hasTags && (
        <span className="encounter-tables__tags" style={{ gridColumn: '2 / -1', gridRow: 2, display: 'flex', flexWrap: 'wrap', gap: '4px', alignItems: 'center', minWidth: 0 }}>
          {overlay && row.tag && <Tag color={GOLD}>{row.tag === 'special' ? 'Special' : 'Legendary'}</Tag>}
          {level && <Tag>{level}</Tag>}
          {ownSeason && <Tag title={conditionLabel(row.condition)}>{conditionLabel(row.condition)}</Tag>}
          {dupe && <Tag title="An evolution family you already have this attempt">Dupe</Tag>}
        </span>
      )}
    </button>
  )
}

function RowGrid({ children }) {
  return (
    <div className="encounter-tables__rows" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '2px 14px' }}>
      {children}
    </div>
  )
}

function RareStrip({ rare, disabled, selectedKey, onJump, onSelect, blockedOf = () => false }) {
  if (rare.length === 0) return null
  return (
    <div className="encounter-tables__strip" style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px', marginBottom: '10px' }}>
      <span style={{ alignSelf: 'center', fontSize: '0.72em', letterSpacing: '0.08em', textTransform: 'uppercase', color: GOLD, whiteSpace: 'nowrap', flexShrink: 0 }}>Rare here</span>
      {rare.map((row, index) => {
        const isStatic = row.slot_kind === 'static'
        const level = levelText(row)
        const where = [row.area, row.condition ? conditionLabel(row.condition) : null].filter(Boolean).join(' · ')
        const selected = isStatic && selectedKey === slotKey(row)
        // A static behind a later split stays listed for planning but
        // cannot be claimed; an overlay's jump still shows its table.
        const blocked = isStatic && blockedOf(row)
        return (
          <button
            key={`${row.slot_kind}-${index}-${row.species_id}`}
            type="button"
            className={`encounter-tables__chip${selected ? ' encounter-tables__chip--selected' : ''}`}
            disabled={disabled || blocked}
            aria-pressed={isStatic ? selected : undefined}
            title={blocked ? 'Not reachable yet' : row.note || (isStatic ? 'A static encounter: select it, then confirm' : 'Show this table')}
            onClick={() => (isStatic ? onSelect(row) : onJump(row))}
            style={{
              opacity: blocked ? 0.5 : 1,
              display: 'inline-flex', alignItems: 'center', gap: '6px', flexShrink: 0,
              padding: '4px 10px 4px 6px', borderRadius: '999px',
              border: `1px solid ${selected ? ACTIVE : GOLD}`,
              background: selected ? 'color-mix(in srgb, var(--pick) 14%, transparent)' : 'color-mix(in srgb, var(--rare) 10%, transparent)',
              color: 'var(--text-primary)',
              font: 'inherit', fontSize: '0.8em', cursor: disabled ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap',
            }}
          >
            <Sprite speciesId={row.species_id} size={24} useIcon />
            <span style={{ fontWeight: 'bold' }}>{row.name}</span>
            <span style={{ color: GOLD }}>{isStatic ? 'Static' : `${row.rate}%`}</span>
            {where && <span style={{ color: 'var(--text-secondary)' }}>{where}</span>}
            {level && <span style={{ color: 'var(--text-secondary)' }}>{level}</span>}
          </button>
        )
      })}
    </div>
  )
}

// The split chip on a table that is not open yet: its split's colour and
// initial, or a dashed "not set" for a gate without a decided split.
function OpensChip({ info, gateLabel }) {
  if (info.state === 'unknown') {
    return <span className="opens-chip opens-chip--unknown">{gateLabel(info.gate)} · split not set</span>
  }
  if (info.state !== 'future' || !info.split) return null
  return (
    <span className="opens-chip" style={{ '--split-color': info.split.color }}>
      <span className="opens-chip__medal" aria-hidden="true">{splitInitial(info.split)}</span>
      Opens in {info.split.label}{info.gate ? ` · ${gateLabel(info.gate)}` : ''}
    </span>
  )
}

function MethodTabs({ tables, activeKey, onPick, infoOf }) {
  const tabRefs = useRef({})
  // Two visible tables of one method (all seasons + a season) need the
  // season to tell them apart.
  const methodCounts = tables.reduce((counts, t) => ({ ...counts, [t.method]: (counts[t.method] || 0) + 1 }), {})
  const move = (event, index) => {
    const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0
    if (!step) return
    event.preventDefault()
    const next = tables[(index + step + tables.length) % tables.length]
    onPick(next.key)
    tabRefs.current[next.key]?.focus()
  }
  return (
    <div className="encounter-tables__tabs" role="tablist" aria-label="Encounter method" style={{ display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '4px', marginBottom: '8px' }}>
      {tables.map((table, index) => {
        const active = table.key === activeKey
        const { meta } = table
        const hue = GROUP_HUES[meta.group] || GROUP_HUES.other
        const label = methodCounts[table.method] > 1 && table.condition ? `${meta.label} · ${conditionLabel(table.condition)}` : meta.label
        const info = infoOf(table)
        const stateClass = info.state === 'future' ? ' encounter-tables__tab--future' : info.state === 'unknown' ? ' encounter-tables__tab--unknown' : ''
        return (
          <button
            key={table.key}
            ref={el => { tabRefs.current[table.key] = el }}
            type="button"
            role="tab"
            id={`encounter-tab-${table.key}`}
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            className={`encounter-tables__tab${stateClass}`}
            title={info.state === 'future' ? `Opens in ${info.split.label}` : info.state === 'unknown' ? 'Behind a gate whose split is not set' : undefined}
            onClick={() => onPick(table.key)}
            onKeyDown={event => move(event, index)}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '7px', flexShrink: 0,
              padding: '4px 12px 4px 4px', borderRadius: '999px', font: 'inherit', fontSize: '0.84em', whiteSpace: 'nowrap', cursor: 'pointer',
              border: `1px solid ${active ? ACTIVE : info.isNew ? info.split?.color || 'var(--border-strong)' : 'var(--border-strong)'}`,
              background: active ? 'color-mix(in srgb, var(--pick) 12%, transparent)' : 'var(--surface-deep)',
              color: active ? ACTIVE : 'var(--text-secondary)',
              '--split-color': info.split?.color || 'var(--border-strong)',
            }}
          >
            <span style={{ width: '26px', height: '26px', borderRadius: '999px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: `${hue}22`, flexShrink: 0 }}>
              <MethodIcon group={meta.group} rare={Boolean(meta.is_rare)} size={18} title={meta.label} />
            </span>
            <span>{label}</span>
            <span style={{ fontVariantNumeric: 'tabular-nums', fontSize: '0.86em', opacity: 0.75 }}>{table.rows.length + table.overlays.length}</span>
            {info.isNew && <span className="opens-chip opens-chip--new">NEW</span>}
            {!info.isNew && info.state === 'future' && <span className="encounter-tables__tab-dot" aria-hidden="true" />}
          </button>
        )
      })}
    </div>
  )
}

function EncounterTables({
  view,
  locationName = 'this location',
  fallbackPool = [],
  dupedFamilyIds = new Set(),
  disabled = false,
  area = null,
  onAreaChange = () => {},
  season = 'spring',
  onSeasonChange = () => {},
  selectedKey = null,
  onSelect = () => {},
  // Split layout: how a row resolves against the run's progress, which
  // split a jump came from (its tables are badged NEW), a request to open
  // the tab of a given method, and the admin Opens-in controls.
  availabilityOf = null,
  newSplitKey = null,
  focus = null,
  gates = [],
  renderTableAdmin = null,
  renderAreaAdmin = null,
}) {
  const [highlightSpecies, setHighlightSpecies] = useState(null)
  // Jumping to a legendary's table shows its season without changing the
  // run's chosen one; picking a season on the switch ends the peek.
  const [peek, setPeek] = useState(null)   // { season, from }
  const [activeKey, setActiveKey] = useState(null)
  // A new run season (picked here or on another location) ends the peek.
  const shownSeason = peek && peek.from === season ? peek.season : season
  useEffect(() => {
    if (highlightSpecies == null) return undefined
    const timer = setTimeout(() => setHighlightSpecies(null), 2500)
    return () => clearTimeout(timer)
  }, [highlightSpecies])

  const areas = view.areas
  const activeArea = areas.some(a => a.key === (area ?? '')) ? (area ?? '') : (areas[0]?.key ?? '')
  const tables = visibleTables(view, activeArea, shownSeason)

  const gateLabel = key => gates.find(g => g.gate_key === key)?.label || key || 'a gate'
  // A table's rows all resolve alike (rules are per table), so one row
  // stands for the table; the rare strip asks about its own rows.
  const infoOf = (table) => {
    const sample = table?.rows?.[0] || table?.overlays?.[0] || null
    const info = availabilityOf && sample ? availabilityOf(sample) : { state: 'open', split: null, gate: null }
    return { ...info, isNew: Boolean(newSplitKey) && sample?.opens_in === newSplitKey }
  }
  const rowBlocked = (row) => Boolean(availabilityOf) && row?.source !== 'search' && availabilityOf(row).state !== 'open'

  // A jump from a split's "New encounters" list lands on the first table
  // of the methods that opened, in its area and season.
  useEffect(() => {
    if (!focus?.nonce) return
    const wanted = new Set(focus.methods || [])
    const target = view.tables.find(t => wanted.has(t.method) && (!focus.areas?.length || focus.areas.includes(t.area || '')))
      || view.tables.find(t => wanted.has(t.method))
    if (!target) return
    onAreaChange(target.area || '')
    const seasons = conditionSeasons(target.condition)
    setPeek(seasons.includes(season) ? null : { season: seasons[0], from: season })
    setActiveKey(target.key)
  }, [focus?.nonce]) // eslint-disable-line react-hooks/exhaustive-deps
  // The chosen tab; else the tab holding the selected species (the tables
  // reopen on it after Undo); else the first one.
  const selectedTable = selectedKey
    ? tables.find(t => t.rows.some(r => slotKey(r) === selectedKey) || t.overlays.some(r => slotKey(r) === selectedKey))
    : null
  const activeTable = tables.find(t => t.key === activeKey) ?? selectedTable ?? tables[0] ?? null
  const empty = view.tables.length === 0 && view.rare.length === 0

  const jumpTo = (row) => {
    onAreaChange(row.area || '')
    const seasons = conditionSeasons(row.condition)
    setPeek(seasons.includes(season) ? null : { season: seasons[0], from: season })
    const host = view.tables.find(t => t.overlays.includes(row))
    if (host) setActiveKey(host.key)
    setHighlightSpecies(row.species_id)
  }
  const chooseSeason = (next) => {
    setPeek(null)
    if (next !== season) onSeasonChange(next)
  }

  // What to say when the chosen area and season show no table.
  const staticsHere = view.rare.some(r => r.slot_kind === 'static' && (r.area || '') === activeArea)
  const emptyMessage = staticsHere
    ? 'No wild tables here: select the static encounter above, or use the search.'
    : view.hasSeasons
      ? `Nothing documented here in ${seasonLabel(shownSeason)}.`
      : 'No wild tables documented here. Use the search to log a gift, trade or static.'

  if (empty) {
    if (fallbackPool.length > 0) {
      // A game without method data (vanilla, for now): the plain pool as
      // one selectable list, no odds.
      return (
        <div className="encounter-tables">
          <div style={{ fontSize: '0.8em', color: 'var(--text-secondary)', marginBottom: '6px' }}>Encounters</div>
          <RowGrid>
            {fallbackPool.map(species => {
              const row = { species_id: species.species_id, name: species.name, method: null, slot_kind: 'slot', source: 'pool' }
              return (
                <OddsRow
                  key={species.species_id}
                  row={row}
                  hue={GROUP_HUES.other}
                  dupe={dupedFamilyIds.has(species.species_id)}
                  disabled={disabled}
                  selected={selectedKey === slotKey(row)}
                  onSelect={onSelect}
                />
              )
            })}
          </RowGrid>
        </div>
      )
    }
    return (
      <div className="encounter-tables encounter-tables--empty" style={{ fontSize: '0.85em', color: 'var(--text-secondary)', padding: '8px 2px' }}>
        No wild encounters documented for {locationName}. Use the search to log a gift, trade or static.
      </div>
    )
  }

  const hue = activeTable ? (GROUP_HUES[activeTable.meta.group] || GROUP_HUES.other) : GROUP_HUES.other
  const overlays = activeTable ? visibleOverlays(activeTable, shownSeason) : []
  const activeInfo = activeTable ? infoOf(activeTable) : { state: 'open', split: null, gate: null, isNew: false }
  const activeBlocked = activeInfo.state !== 'open'

  return (
    <div className="encounter-tables">
      <RareStrip rare={view.rare} disabled={disabled} selectedKey={selectedKey} onJump={jumpTo} onSelect={onSelect} blockedOf={rowBlocked} />

      {(areas.length > 1 || view.hasSeasons) && (
        <div className="encounter-tables__context" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
          {areas.length > 1 && (
            <div aria-label="Area" role="group" style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {areas.map(a => {
                const active = a.key === activeArea
                return (
                  <button
                    key={a.key || 'whole'}
                    type="button"
                    aria-pressed={active}
                    className="encounter-tables__area"
                    onClick={() => { setPeek(null); onAreaChange(a.key) }}
                    style={{ ...PILL_STYLE, borderColor: active ? 'var(--accent)' : 'var(--border-strong)', background: active ? 'var(--accent-bg)' : 'var(--surface-deep)', color: active ? 'var(--accent)' : 'var(--text-secondary)' }}
                  >
                    {a.label || locationName}
                  </button>
                )
              })}
              {renderAreaAdmin && activeArea && renderAreaAdmin(activeArea)}
            </div>
          )}
          {view.hasSeasons && (
            <div role="group" aria-label="Season" title="Season follows your DS clock" style={{ display: 'flex', gap: '4px', marginLeft: areas.length > 1 ? 'auto' : 0 }}>
              {SEASONS.map(s => {
                const active = s === shownSeason
                return (
                  <button
                    key={s}
                    type="button"
                    aria-pressed={active}
                    className="encounter-tables__season"
                    onClick={() => chooseSeason(s)}
                    style={{ ...PILL_STYLE, padding: '4px 9px', borderColor: active ? 'var(--accent)' : 'var(--border-strong)', background: active ? 'var(--accent-bg)' : 'var(--surface-deep)', color: active ? 'var(--accent)' : 'var(--text-secondary)' }}
                  >
                    {seasonLabel(s)}
                  </button>
                )
              })}
            </div>
          )}
        </div>
      )}

      {!activeTable ? (
        <div className="encounter-tables__empty" style={{ fontSize: '0.85em', color: 'var(--text-secondary)', padding: '8px 2px' }}>
          {emptyMessage}
        </div>
      ) : (
        <>
          <MethodTabs tables={tables} activeKey={activeTable.key} onPick={setActiveKey} infoOf={infoOf} />
          <div className={`encounter-tables__panel${activeBlocked ? ' encounter-tables__panel--blocked' : ''}`} role="tabpanel" aria-labelledby={`encounter-tab-${activeTable.key}`}>
            {/* No prose and no rare label: the tab names the method and
                marks a rare spot with its sparkle. Only the season shows. */}
            {(activeTable.condition || activeBlocked || renderTableAdmin) && (
              <div className="encounter-tables__about" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '6px 8px', fontSize: '0.8em', color: 'var(--text-secondary)', margin: '2px 2px 8px' }}>
                {activeTable.condition && <Tag title="Season-specific table">{conditionLabel(activeTable.condition)}</Tag>}
                {activeBlocked && (
                  <span className="encounter-tables__blocked" style={{ margin: 0 }}>
                    <OpensChip info={activeInfo} gateLabel={gateLabel} />
                    <span>{activeInfo.state === 'unknown' ? 'Set the gate’s split from Game flags to use this table.' : 'Not reachable yet: it cannot be used for this location’s encounter.'}</span>
                  </span>
                )}
                {renderTableAdmin && <span style={{ marginLeft: 'auto' }}>{renderTableAdmin(activeTable)}</span>}
              </div>
            )}
            <RowGrid>
              {/* A table may list one species twice at one rate (split by
                  level), so rows are keyed by position. */}
              {activeTable.rows.map((row, index) => (
                <OddsRow
                  key={`slot-${index}-${row.species_id}`}
                  row={row}
                  hue={hue}
                  dupe={dupedFamilyIds.has(row.species_id)}
                  disabled={disabled || activeBlocked}
                  highlighted={highlightSpecies === row.species_id}
                  selected={selectedKey === slotKey(row)}
                  onSelect={onSelect}
                />
              ))}
              {overlays.length > 0 && activeTable.rows.length > 0 && (
                <div aria-hidden="true" style={{ gridColumn: '1 / -1', borderTop: '1px dashed color-mix(in srgb, var(--rare) 45%, transparent)', margin: '4px 6px' }} />
              )}
              {overlays.map((row, index) => (
                <OddsRow
                  key={`overlay-${index}-${row.species_id}`}
                  row={row}
                  hue={hue}
                  dupe={dupedFamilyIds.has(row.species_id)}
                  disabled={disabled || activeBlocked}
                  highlighted={highlightSpecies === row.species_id}
                  selected={selectedKey === slotKey(row)}
                  onSelect={onSelect}
                  overlay
                  tableCondition={activeTable.condition}
                />
              ))}
            </RowGrid>
          </div>
        </>
      )}
    </div>
  )
}

export default EncounterTables
