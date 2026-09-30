import { BATTLE_FORMATS, normalizeBattleFormat } from '../utils/battleFormat'

// A see-through sash across a trainer card, left of the level cap and
// Battle button, running from the card's top edge down to the right.
// Its slot takes the full height of the summary row; the band is clipped
// to the slot, so its ends are cut by the card's top and bottom edges.
function BattleFormatSash({ format, open = false }) {
  const normalized = normalizeBattleFormat(format)
  if (!normalized) return null
  const { color, rgb, label, pips } = BATTLE_FORMATS[normalized]
  return (
    <span
      className={`trainer-card-summary__sash${open ? ' trainer-card-summary__sash--open' : ''}`}
      style={{ '--format-color': color, '--format-rgb': rgb }}
      role="img"
      aria-label={`${label} battle`}
      title={`${label} battle`}
    >
      <span className="trainer-card-summary__sash-clip" aria-hidden="true">
        <span className="trainer-card-summary__sash-band">
          {normalized === 'rotation' ? (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 12a8 8 0 0 1-13.7 5.6" /><path d="M4 12a8 8 0 0 1 13.7-5.6" /><path d="M18 3v4h-4" /><path d="M6 21v-4h4" />
            </svg>
          ) : (
            <span className="trainer-card-summary__sash-pips">
              {Array.from({ length: pips }, (_, i) => <span key={i} />)}
            </span>
          )}
          <span>{label}</span>
        </span>
      </span>
    </span>
  )
}

export default BattleFormatSash
