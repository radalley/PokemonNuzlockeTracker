import { useEffect, useState } from 'react'

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

  useEffect(() => {
    setValues(getComputedVars())
  }, [])

  if (!isOpen) return null

  const miniBtn = { padding: '2px 8px', fontSize: '0.75em', cursor: 'pointer', borderRadius: '999px', border: '1px solid var(--border-strong)', background: 'var(--surface-mid)', color: 'var(--text-secondary)', font: 'inherit', lineHeight: '1.4' }

  return (
    <div style={{
      position: 'fixed',
      right: 'max(8px, calc((100vw - 1380px) / 2 + 28px - 262px))',
      top: '120px',
      width: '230px',
      zIndex: 900,
      border: '1px solid var(--border-strong)',
      borderRadius: '12px',
      background: 'var(--surface)',
      padding: '10px 12px',
      fontSize: '0.72rem',
      fontFamily: 'Consolas, monospace',
      overflowY: 'auto',
      maxHeight: 'calc(100vh - 160px)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ fontWeight: 'bold', color: 'var(--text-primary)', fontSize: '0.78rem', fontFamily: 'inherit' }}>
          Palette Debug
        </div>
        {onToggle && <button onClick={onToggle} title="Minimize" style={miniBtn}>−</button>}
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
  )
}
