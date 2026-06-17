import { useEffect, useState, useCallback } from 'react'
import { apiFetch } from '../utils/api'

const TOKENS = [
  { group: 'Text', vars: ['--text-primary', '--text-secondary'] },
  { group: 'Page', vars: ['--bg-page'] },
  { group: 'Surface', vars: ['--surface', '--surface-mid', '--surface-deep'] },
  { group: 'Border', vars: ['--border', '--border-strong'] },
  { group: 'Accent', vars: ['--accent', '--accent-bg', '--accent-border'] },
]

function getComputedVars() {
  const style = getComputedStyle(document.documentElement)
  const result = {}
  TOKENS.forEach(({ vars }) => vars.forEach(v => {
    result[v] = style.getPropertyValue(v).trim()
  }))
  return result
}

export default function PaletteDebugPanel({ isOpen = true, onToggle = null }) {
  const [values, setValues] = useState({})
  const [allSpecies, setAllSpecies] = useState([])
  const [brokenIds, setBrokenIds] = useState(new Set())
  const [validFilter, setValidFilter] = useState('all') // 'all' | 'valid' | 'invalid'
  const [trainerPics, setTrainerPics] = useState([])
  const [brokenPics, setBrokenPics] = useState(new Set())

  useEffect(() => {
    setValues(getComputedVars())
  }, [])

  useEffect(() => {
    if (!isOpen) return
    apiFetch('/api/species/search?q=')
      .then(r => r.json())
      .then(data => setAllSpecies(data))
      .catch(() => {})
    apiFetch('/api/debug/trainer-pics')
      .then(r => r.json())
      .then(data => setTrainerPics(data))
      .catch(() => {})
  }, [isOpen])

  const handleImgError = useCallback((speciesId) => {
    setBrokenIds(prev => new Set(prev).add(speciesId))
  }, [])

  const handlePicError = useCallback((pic) => {
    setBrokenPics(prev => new Set(prev).add(pic))
  }, [])

  if (!isOpen) return null

  const miniBtn = { padding: '2px 8px', fontSize: '0.75em', cursor: 'pointer', borderRadius: '999px', border: '1px solid var(--border-strong)', background: 'var(--surface-mid)', color: 'var(--text-secondary)', font: 'inherit', lineHeight: '1.4' }

  return (
    <div style={{
      position: 'fixed',
      right: '8px',
      top: '120px',
      width: '720px',
      zIndex: 900,
      border: '1px solid var(--border-strong)',
      borderRadius: '12px',
      background: 'var(--surface)',
      padding: '10px 12px',
      fontSize: '0.72rem',
      fontFamily: 'Consolas, monospace',
      maxHeight: 'calc(100vh - 160px)',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px', flexShrink: 0 }}>
        <div style={{ fontWeight: 'bold', color: 'var(--text-primary)', fontSize: '0.78rem', fontFamily: 'inherit' }}>
          Debug Panel
        </div>
        {onToggle && <button onClick={onToggle} title="Minimize" style={miniBtn}>−</button>}
      </div>

      {/* Three columns */}
      <div style={{ display: 'flex', gap: '12px', minHeight: 0, flex: 1 }}>

        {/* Left: Palette */}
        <div style={{ width: '210px', flexShrink: 0, overflowY: 'auto' }}>
          <div style={{ color: 'var(--text-secondary)', marginBottom: '6px', fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Palette
          </div>
          {TOKENS.map(({ group, vars }) => (
            <div key={group} style={{ marginBottom: '8px' }}>
              <div style={{ color: 'var(--text-secondary)', marginBottom: '4px', fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                {group}
              </div>
              {vars.map(v => {
                const val = values[v] || ''
                return (
                  <div key={v} style={{ display: 'flex', alignItems: 'center', gap: '7px', marginBottom: '3px' }}>
                    <div style={{
                      width: '20px',
                      height: '20px',
                      borderRadius: '4px',
                      background: `var(${v})`,
                      border: '1px solid var(--border-strong)',
                      flexShrink: 0,
                    }} />
                    <div style={{ overflow: 'hidden' }}>
                      <div style={{ color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {v}
                      </div>
                      <div style={{ color: 'var(--text-secondary)', fontSize: '0.66rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {val}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          ))}
        </div>

        {/* Divider */}
        <div style={{ width: '1px', background: 'var(--border-strong)', flexShrink: 0 }} />

        {/* Middle: Pokemon sprite list */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px', flexShrink: 0 }}>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Sprites ({allSpecies.length})
            </div>
            {brokenIds.size > 0 && (
              <div style={{ color: '#e55', fontSize: '0.68rem', fontWeight: 'bold' }}>
                missing: {brokenIds.size}
              </div>
            )}
          </div>
          {/* Filter pills */}
          <div style={{ display: 'flex', gap: '4px', marginBottom: '6px', flexShrink: 0 }}>
            {[['all', 'All'], ['valid', 'Valid'], ['invalid', 'Invalid']].map(([key, label]) => (
              <button
                key={key}
                onClick={() => setValidFilter(key)}
                style={{
                  padding: '2px 7px',
                  fontSize: '0.66rem',
                  cursor: 'pointer',
                  borderRadius: '999px',
                  border: '1px solid var(--border-strong)',
                  background: validFilter === key ? 'var(--accent)' : 'var(--surface-mid)',
                  color: validFilter === key ? '#fff' : 'var(--text-secondary)',
                  font: 'inherit',
                  lineHeight: '1.4',
                }}
              >
                {label}
              </button>
            ))}
          </div>
          <div style={{ overflowY: 'auto', flex: 1 }}>
            {allSpecies.length === 0 && (
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.68rem' }}>Loading…</div>
            )}
            {allSpecies
              .filter(s => {
                if (validFilter === 'valid') return s.valid === 'true'
                if (validFilter === 'invalid') return s.valid === 'false'
                return true
              })
              .map(s => {
              const isBroken = brokenIds.has(s.species_id)
              const isValid = s.valid === 'true'
              return (
                <div key={s.species_id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '2px 4px',
                  borderRadius: '4px',
                  background: isBroken ? 'rgba(238,85,85,0.12)' : 'transparent',
                  borderLeft: isBroken ? '2px solid #e55' : '2px solid transparent',
                  marginBottom: '1px',
                }}>
                  <img
                    src={`/sprites/Standard/${s.species_id}.png`}
                    width={28}
                    height={28}
                    alt=""
                    style={{ imageRendering: 'pixelated', objectFit: 'contain', flexShrink: 0, opacity: isBroken ? 0.3 : 1 }}
                    onError={() => handleImgError(s.species_id)}
                  />
                  <div style={{ overflow: 'hidden', flex: 1 }}>
                    <div style={{ color: isBroken ? '#e55' : 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {s.name}
                    </div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.66rem' }}>
                      #{s.species_id}
                    </div>
                  </div>
                  {!isValid && (
                    <div style={{ fontSize: '0.6rem', color: '#888', flexShrink: 0, border: '1px solid #444', borderRadius: '3px', padding: '0 3px' }}>
                      inv
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Divider */}
        <div style={{ width: '1px', background: 'var(--border-strong)', flexShrink: 0 }} />

        {/* Right: Trainer pic list */}
        <div style={{ width: '180px', flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px', flexShrink: 0 }}>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Trainer Pics ({trainerPics.length})
            </div>
            {brokenPics.size > 0 && (
              <div style={{ color: '#e55', fontSize: '0.68rem', fontWeight: 'bold' }}>
                missing: {brokenPics.size}
              </div>
            )}
          </div>
          <div style={{ overflowY: 'auto', flex: 1 }}>
            {trainerPics.length === 0 && (
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.68rem' }}>Loading…</div>
            )}
            {trainerPics.map(pic => {
              const isBroken = brokenPics.has(pic)
              return (
                <div key={pic} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '2px 4px',
                  borderRadius: '4px',
                  background: isBroken ? 'rgba(238,85,85,0.12)' : 'transparent',
                  borderLeft: isBroken ? '2px solid #e55' : '2px solid transparent',
                  marginBottom: '1px',
                }}>
                  <img
                    src={`/sprites/trainers/gen3/${pic}.png`}
                    width={40}
                    height={40}
                    alt=""
                    style={{ imageRendering: 'pixelated', objectFit: 'contain', flexShrink: 0, opacity: isBroken ? 0.3 : 1 }}
                    onError={() => handlePicError(pic)}
                  />
                  <div style={{ overflow: 'hidden', flex: 1 }}>
                    <div style={{ color: isBroken ? '#e55' : 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontSize: '0.65rem' }}>
                      {pic}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

      </div>
    </div>
  )
}
