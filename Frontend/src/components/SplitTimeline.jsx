import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Sprite from './Sprite'
import { Button } from './Button'
import TypeIcon from './TypeIcon'
import { getTrainerSpriteSrc } from './trainerSprite'
import { getBattleRecords, getSplitCatalogue } from '../utils/dataLayer'
import { SplitItemEditor, SplitItems } from './SplitItems'
import { titleCase } from '../utils/splitItems'
import './SplitTimeline.css'
import useDockedPanels from '../utils/useDockedPanels'

/** Shared with the future victory recap: history comes from battle records,
 * never reconstructed from the current Box/party or current death status. */
export default function SplitTimeline({ runId, attemptId, gameId, generation, starter, script = [], refreshKey = 0, editMode = false }) {
  const preferenceKey = `lockley:splits:${runId}:${attemptId}`
  const [filter, setFilter] = useState(() => {
    try { return ['all', 'parties', 'items'].includes(sessionStorage.getItem(preferenceKey)) ? sessionStorage.getItem(preferenceKey) : 'all' }
    catch { return 'all' }
  })
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  const [editor, setEditor] = useState(null)
  const [notice, setNotice] = useState('')
  const docked = useDockedPanels()
  const [expandedOverride, setExpanded] = useState(() => window.location.hash.startsWith('#split-') ? true : null)
  const expanded = docked ? true : (expandedOverride ?? false)
  const [closed, setClosed] = useState(new Set())

  useEffect(() => {
    if (!gameId) return
    let active = true
    Promise.all([getSplitCatalogue(gameId, starter), getBattleRecords(runId, attemptId)])
      .then(([catalogue, records]) => {
        if (active) { setData({ ...catalogue, records }); setError('') }
      })
      .catch(err => { if (active) setError(err.message) })
    return () => { active = false }
  }, [gameId, starter, runId, attemptId, refreshKey, revision])

  useEffect(() => {
    if (!data) return
    const id = window.location.hash.slice(1)
    if (!id.startsWith('split-')) return
    const frame = requestAnimationFrame(() => document.getElementById(decodeURIComponent(id))?.scrollIntoView({ block: 'center' }))
    return () => cancelAnimationFrame(frame)
  }, [data])

  const chooseFilter = value => {
    setFilter(value)
    try { sessionStorage.setItem(preferenceKey, value) } catch { /* private browsing */ }
  }
  const openEditor = item => {
    setNotice('')
    setEditor(item ? { ...item } : { split_key: data?.splits.find(s => s.kind === 'gym')?.split_key || '', item_name: '', method: '' })
  }
  const records = data?.records || []
  const defeatedIds = new Set(script.filter(s => s.is_defeated).map(s => Number(s.event_id)))
  let nextAssigned = false

  return <>
    {!docked && expanded && <button type="button" className="attempt-panel-backdrop" aria-label="Close splits panel" onClick={() => setExpanded(false)} />}
    <aside className={`split-timeline ${expanded ? 'split-timeline--open' : ''}`} aria-label="Split timeline">
    <div className="split-timeline__heading">
      {docked
        ? <h2 className="split-timeline__title">Splits</h2>
        : <button type="button" className="split-timeline__toggle" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>Splits <span>{expanded ? '−' : '+'}</span></button>}
      {editMode && expanded && data?.splits.some(s => s.kind === 'gym') && <Button size="sm" tone="success" onClick={() => openEditor(null)}>+ Add item</Button>}
    </div>
    <div className="split-timeline__contents" hidden={!expanded}>
      <div className="split-timeline__filters" aria-label="Split content">
        {['all', 'parties', 'items'].map(value => <Button key={value} size="sm" selected={filter === value} aria-pressed={filter === value} onClick={() => chooseFilter(value)}>{titleCase(value)}</Button>)}
      </div>
      {error && <div role="alert">{error} <Button size="sm" onClick={() => setRevision(r => r + 1)}>Retry</Button></div>}
      {!data && !error && <p role="status">Loading splits…</p>}
      {notice && <p className="split-timeline__notice" role="status">{notice}</p>}
      {editMode && editor && <SplitItemEditor gameId={gameId} editor={editor} setEditor={setEditor} splits={data.splits.filter(s => s.kind === 'gym')}
        onSaved={() => { setNotice('Item saved for this game.'); setRevision(r => r + 1) }}
        onRemoved={() => { setNotice('Item removed.'); setRevision(r => r + 1) }} />}
      {data?.splits.length === 0 && <p>No split battles are configured for this game.</p>}
      {data?.splits.map((split, index) => {
        const record = records.find(r => r.split_key === split.split_key || Number(r.boss_event_id) === Number(split.event_id) || Number(r.trainer_id) === Number(split.trainer_id))
        const defeated = !!record || defeatedIds.has(Number(split.trainer_id))
        const next = !defeated && !nextAssigned
        if (next) nextAssigned = true
        const items = split.kind === 'gym' ? data.items.filter(i => i.split_key === split.split_key) : []
        const leagueStart = split.kind !== 'gym' && (index === 0 || data.splits[index - 1].kind === 'gym')
        const name = titleCase(split.trainer_name || split.encounter_title)
        const portrait = getTrainerSpriteSrc(split.trainer_pic, split.trainer_class, split.trainer_name, gameId, split.version_group_id, generation)
        const anchor = `split-${split.split_key}`
        return <section key={split.split_key} id={anchor} className="split-timeline__entry">
          {leagueStart && <h3 className="split-timeline__league">Pokémon League</h3>}
          <div className={`split-card ${defeated ? 'split-card--defeated' : ''} ${next ? 'split-card--next' : ''}`}>
            <button type="button" className="split-card__head" aria-expanded={!closed.has(split.split_key)} onClick={() => setClosed(old => { const value = new Set(old); value.has(split.split_key) ? value.delete(split.split_key) : value.add(split.split_key); return value })}>
              {portrait && <img src={portrait} alt="" className="split-card__portrait" onError={e => { e.currentTarget.style.visibility = 'hidden' }} />}
              <span className="split-card__identity"><strong>{name}</strong>{split.type_focus ? <TypeIcon type={split.type_focus} height={12} /> : <small>{split.kind === 'champion' ? 'Champion' : split.kind === 'elite_four' ? 'Elite Four' : 'Gym Leader'}</small>}</span>
              {split.badge_id && <img className="split-card__badge" src={`/sprites/Badges/${split.badge_id}.png`} alt="" />}
              <span className="split-card__status">{defeated ? '✓ Defeated' : next ? 'Up next' : 'Upcoming'}</span>
            </button>
            <div hidden={closed.has(split.split_key)}>
              {filter !== 'items' && record?.party.length > 0 && <div className="split-card__party">
                {record.party.map(member => {
                  const label = `${member.nickname || member.species_name || 'Pokémon'} · ${member.species_name || 'Recorded form'}${member.died_in_battle ? ' · Fell in this battle' : ''}`
                  const content = <><Sprite speciesId={member.species_id} shiny={member.shiny === true || member.shiny === 'True'} female={member.gender?.toLowerCase() === 'female'} size={40} alt={label} />{member.died_in_battle && <span aria-hidden="true">×</span>}</>
                  return member.available === false ? <span key={member.slot} className={`split-card__mon ${member.died_in_battle ? 'split-card__mon--fallen' : ''}`} title={`${label} · No longer in Box`}>{content}</span> :
                    <Link key={member.slot} className={`split-card__mon ${member.died_in_battle ? 'split-card__mon--fallen' : ''}`} title={label} aria-label={`Open ${label} in Box`} to={`/box/${runId}/${attemptId}?pokemon=${member.pokemon_id}`} state={{ fromSplit: `/attempt/${runId}/${attemptId}#${encodeURIComponent(anchor)}` }}>{content}</Link>
                })}
              </div>}
              {filter !== 'items' && defeated && !record?.party.length && <p className="split-card__empty">Party not recorded</p>}
              {filter !== 'parties' && split.kind === 'gym' && <SplitItems items={items} name={name} editMode={editMode} openEditor={openEditor} />}
            </div>
          </div>
        </section>
      })}
    </div>
  </aside></>
}
