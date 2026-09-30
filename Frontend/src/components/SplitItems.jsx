import { useState } from 'react'
import Sprite from './Sprite'
import { Button } from './Button'
import { saveSplitItem } from '../utils/dataLayer'
import { chanceLabel, itemGroups, sourcesFor, spriteName, titleCase } from '../utils/splitItems'

// A split's curated item library (shared by every run of the game), grouped
// by how each item is obtained, plus the admin editor. Used by the split
// timeline panel and, for split-layout games, by each split's section.

export function SplitItems({ items, name, editMode, openEditor }) {
  const groups = itemGroups.map(([key, label]) => ({ key, label, items: items
    .map(item => ({ item, sources: sourcesFor(item).filter(source => source.method_kind === key) }))
    .filter(entry => entry.sources.length)
    .sort((a, b) => a.item.item_name.localeCompare(b.item.item_name))
  })).filter(group => group.items.length)
  return <div className="split-card__items"><small>Items</small>
    {items.length ? <div className="split-item-groups" aria-label={`${name} items`}>{groups.map(group =>
      <details key={group.key} className={`split-item-group split-item-group--${group.key}`}>
        <summary><span>{group.label}</span><small>{group.items.length}</small></summary>
        <div className="split-item-group__list">{group.items.map(({ item, sources }) =>
          <details className="split-item" key={`${group.key}:${item.item_record_id}`}>
            <summary>
              <img src={`/sprites/Items/${spriteName(item.item_name)}.png`} alt="" onError={e => { e.currentTarget.style.visibility = 'hidden' }} />
              <span>{item.item_name}</span><small>{chanceLabel(sources)}</small>
            </summary>
            <div className="split-item__sources">{sources.map(source => <div className="split-item__source" key={source.item_source_id || `${source.source_key}:${source.source_detail}`}>
              {source.source_species_id && <Sprite speciesId={source.source_species_id} size={28} alt={source.species_name || ''} />}
              <span><strong>{source.species_name || source.source_detail || item.method}</strong>
                {source.species_name && source.source_detail && source.source_detail !== source.species_name && <small>{source.source_detail}</small>}</span>
              {Number.isFinite(Number(source.chance_percent)) && <b>{Number(source.chance_percent)}%</b>}
            </div>)}</div>
            {editMode && <Button appearance="ghost" size="sm" className="split-card__edit" aria-label={`Edit ${item.item_name}`} onClick={() => openEditor(item)}>Edit item</Button>}
          </details>
        )}</div>
      </details>
    )}</div> : <p className="split-card__empty">No items recorded</p>}
  </div>
}

/**
 * The admin item form: exactly split / item / method, saved through the
 * shared endpoint. `splits` are the gym splits the item may attach to.
 */
export function SplitItemEditor({ gameId, editor, setEditor, splits, onSaved, onRemoved, splitLabel = s => titleCase(s.trainer_name || s.encounter_title || s.label) }) {
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const save = async event => {
    event.preventDefault()
    if (saving) return
    setSaving(true); setSaveError('')
    try {
      await saveSplitItem(gameId, editor, editor.item_record_id ? 'PATCH' : 'POST')
      setEditor(null); onSaved?.()
    } catch (err) { setSaveError(err.message) }
    finally { setSaving(false) }
  }
  const remove = async () => {
    if (!editor?.item_record_id || saving) return
    if (!window.confirm(`Remove ${editor.item_name} from this game's item library?`)) return
    setSaving(true); setSaveError('')
    try {
      await saveSplitItem(gameId, editor, 'DELETE')
      setEditor(null); onRemoved?.()
    } catch (err) { setSaveError(err.message) }
    finally { setSaving(false) }
  }
  return <form className="split-timeline__editor" onSubmit={save}>
    <div className="split-timeline__heading"><strong>{editor.item_record_id ? 'Edit item' : 'Add item'}</strong><Button size="sm" disabled={saving} onClick={() => setEditor(null)}>Cancel</Button></div>
    <label>Split<select value={editor.split_key} onChange={e => setEditor({ ...editor, split_key: e.target.value })} disabled={saving} required>
      {splits.map(s => <option key={s.split_key} value={s.split_key}>{splitLabel(s)}</option>)}
    </select></label>
    <label>Item<input value={editor.item_name} maxLength={100} required disabled={saving} onChange={e => setEditor({ ...editor, item_name: e.target.value })} placeholder="Sitrus Berry" /></label>
    <label>Method<input value={editor.method} maxLength={500} required disabled={saving} onChange={e => setEditor({ ...editor, method: e.target.value })} placeholder="Thief - Audino 5%" /></label>
    <small>Shared across this game’s runs.</small>
    {saveError && <p role="alert">{saveError}</p>}
    <div className="split-timeline__heading"><Button type="submit" tone="success" appearance="solid" disabled={saving}>{saving ? 'Saving…' : editor.item_record_id ? 'Save item' : 'Add to split'}</Button>
      {editor.item_record_id && <Button tone="danger" appearance="outline" disabled={saving} onClick={remove}>Remove</Button>}
    </div>
  </form>
}
