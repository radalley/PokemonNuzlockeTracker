const BATTLE_FORMAT_STYLES = {
  double: { color: '#7ec8e3', label: 'Double' },
  triple: { color: '#f2b46b', label: 'Triple' },
  rotation: { color: '#b48ce3', label: 'Rotation' },
}

export function normalizeBattleFormat(value) {
  const key = String(value || '').trim().toLowerCase()
  return BATTLE_FORMAT_STYLES[key] ? key : null
}

function BattleFormatPill({ format, fontSize = '0.68em' }) {
  const normalized = normalizeBattleFormat(format)
  if (!normalized) return null
  const { color, label } = BATTLE_FORMAT_STYLES[normalized]
  return (
    <span
      title={`${label} battle`}
      style={{
        fontSize,
        color,
        border: `1px solid ${color}`,
        borderRadius: '999px',
        padding: '2px 8px',
        whiteSpace: 'nowrap',
        flexShrink: 0,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
      }}
    >
      {label}
    </span>
  )
}

export default BattleFormatPill
