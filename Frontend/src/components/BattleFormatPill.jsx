import { BATTLE_FORMATS, normalizeBattleFormat } from '../utils/battleFormat'

function BattleFormatPill({ format, fontSize = '0.68em', className = '' }) {
  const normalized = normalizeBattleFormat(format)
  if (!normalized) return null
  const { color, label } = BATTLE_FORMATS[normalized]
  return (
    <span
      className={className || undefined}
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
