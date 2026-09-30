import { useEffect, useRef, useState } from 'react'
import { saveAvailabilityRule } from '../utils/dataLayer'
import { splitInitial } from '../utils/splitFeed'
import { Button } from './Button'

// The admin "Opens in" control (edit mode): a pill showing how a location,
// area, table or trainer resolves, and a popover to set an explicit split,
// a gate, or go back to inheriting. Saving re-resolves the whole page.
export default function OpensInPicker({
  gameId, subjectKind, subjectKey, subjectLabel,
  current = {}, inheritedLabel = 'the default',
  splits = [], gates = [], index = new Map(),
  onSaved = null, align = 'left',
}) {
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState('inherit')      // 'inherit' | 'split' | 'gate'
  const [choice, setChoice] = useState(null)
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const rootRef = useRef(null)
  const rule = current.opens_rule || null
  const explicit = Boolean(rule)

  useEffect(() => {
    if (!open) return undefined
    const close = event => { if (rootRef.current && !rootRef.current.contains(event.target)) setOpen(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  const openPicker = () => {
    setError('')
    setMode(rule?.gate_key ? 'gate' : rule?.opens_in ? 'split' : 'inherit')
    setChoice(rule?.gate_key || rule?.opens_in || null)
    setNote(rule?.note || '')
    setOpen(true)
  }

  const save = async () => {
    if (saving) return
    if (mode !== 'inherit' && !choice) { setError('Pick a split or a gate'); return }
    setSaving(true); setError('')
    try {
      await saveAvailabilityRule(gameId, subjectKind, subjectKey, mode === 'inherit'
        ? {}
        : { opensIn: mode === 'split' ? choice : null, gateKey: mode === 'gate' ? choice : null, note })
      setOpen(false)
      onSaved?.()
    } catch (err) { setError(err.message) }
    finally { setSaving(false) }
  }

  const resolvedSplit = current.opens_in ? index.get(current.opens_in) : null
  const gateLabel = key => gates.find(g => g.gate_key === key)?.label || key
  const summary = current.opens_unknown
    ? `${gateLabel(current.opens_gate)} · not set`
    : resolvedSplit ? resolvedSplit.label : inheritedLabel
  const pillText = explicit ? `Opens in: ${summary}` : `Inherits · ${summary}`

  return (
    <span ref={rootRef} className="opens-in" onClick={event => event.stopPropagation()}>
      <button type="button" className={`opens-in__button${explicit ? '' : ' opens-in__button--inherit'}`} onClick={open ? () => setOpen(false) : openPicker} aria-expanded={open} title={`Set when ${subjectLabel} opens`}>
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
        {pillText}
      </button>
      {open && (
        <div className={`opens-in__pop${align === 'right' ? ' opens-in__pop--right' : ''}`} role="dialog" aria-label={`Opens in: ${subjectLabel}`}>
          <div className="opens-in__title">Opens in</div>
          <div>{subjectLabel} · {subjectKind} rule</div>
          <div className="opens-in__row">
            <Button size="sm" tone="accent" selected={mode === 'inherit'} aria-pressed={mode === 'inherit'} onClick={() => { setMode('inherit'); setChoice(null) }}>Inherit · {inheritedLabel}</Button>
          </div>
          <div>A split</div>
          <div className="opens-in__row">
            {splits.map(split => (
              <button
                key={split.split_key}
                type="button"
                className="opens-in__medal"
                style={{ '--split-color': index.get(split.split_key)?.color || 'var(--border-strong)' }}
                aria-pressed={mode === 'split' && choice === split.split_key}
                title={split.label}
                aria-label={split.label}
                onClick={() => { setMode('split'); setChoice(split.split_key) }}
              >
                {splitInitial(split)}
              </button>
            ))}
          </div>
          {gates.length > 0 && (
            <>
              <div>A gate</div>
              <div className="opens-in__row">
                {gates.map(gate => (
                  <Button key={gate.gate_key} size="sm" tone="accent" selected={mode === 'gate' && choice === gate.gate_key} aria-pressed={mode === 'gate' && choice === gate.gate_key} onClick={() => { setMode('gate'); setChoice(gate.gate_key) }}>
                    {gate.label}
                    <small style={{ opacity: 0.75 }}>{gate.opens_in ? (index.get(gate.opens_in)?.label || gate.opens_in) : 'not set'}</small>
                  </Button>
                ))}
              </div>
            </>
          )}
          {mode !== 'inherit' && (
            <input className="opens-in__note" value={note} onChange={e => setNote(e.target.value)} placeholder="Note (why)" maxLength={500} aria-label="Note" />
          )}
          {error && <div role="alert" style={{ color: '#e05252' }}>{error}</div>}
          <div className="opens-in__actions">
            <Button size="sm" onClick={() => setOpen(false)} disabled={saving}>Cancel</Button>
            <Button size="sm" tone="accent" appearance="solid" onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save'}</Button>
          </div>
        </div>
      )}
    </span>
  )
}
