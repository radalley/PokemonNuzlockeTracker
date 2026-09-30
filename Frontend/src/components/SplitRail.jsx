import { splitInitial } from '../utils/splitFeed'

// The right-gutter medallions: one per visible split. Done are filled,
// the current one is ringed and labelled, future ones are outlined.
export default function SplitRail({ sections, onJump }) {
  const visible = sections.filter(section => !section.hidden)
  if (visible.length === 0) return null
  return (
    <nav className="split-rail" aria-label="Jump to split">
      {visible.map(section => {
        const { split } = section
        const label = [split.label, split.type_focus, split.level_cap != null ? `Lv ${split.level_cap}` : null].filter(Boolean).join(' · ')
        return (
          <button
            key={section.key}
            type="button"
            className={`split-rail__medal split-rail__medal--${section.state}`}
            style={{ '--split-color': section.color }}
            title={label}
            aria-label={`${label}: ${section.state === 'done' ? 'defeated' : section.state === 'current' ? 'current split' : 'upcoming'}`}
            aria-current={section.state === 'current' ? 'step' : undefined}
            onClick={() => onJump(section.key)}
          >
            {section.state === 'done'
              ? <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-10" /></svg>
              : splitInitial(split)}
            <span className="split-rail__label" aria-hidden="true">{label}</span>
          </button>
        )
      })}
    </nav>
  )
}
