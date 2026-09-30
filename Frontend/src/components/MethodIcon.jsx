// A glyph per encounter-method group, drawn inline so it reads in both
// themes and needs no asset. Rare spots get a sparkle ring.
import { GROUP_HUES } from '../utils/encounterTables'

const PATHS = {
  // three blades of grass
  grass: 'M4 20 C6 14 7 10 7 6 C9 10 10 14 10 20 M10 20 C11 13 12 9 13 4 C14 9 15 13 15 20 M15 20 C16 15 17 12 20 8 C19 12 18 16 18 20',
  // a cave arch
  cave: 'M3 20 L3 12 C3 6 21 6 21 12 L21 20 M8 20 L8 14 C8 11 16 11 16 14 L16 20',
  // dunes
  ground: 'M2 18 C6 12 9 12 12 16 C15 20 18 10 22 14 M2 21 L22 21',
  // a doorway
  indoor: 'M5 21 L5 5 L19 5 L19 21 M9 21 L9 11 L15 11 L15 21',
  // an arc with its shadow
  bridge: 'M2 14 C7 6 17 6 22 14 M4 18 L20 18 M6 14 L6 18 M12 10 L12 18 M18 14 L18 18',
  // a wave
  water: 'M2 12 C5 8 7 8 10 12 C13 16 15 16 18 12 C20 9 21 9 22 10 M2 18 C5 14 7 14 10 18 C13 22 15 22 18 18',
  // a hook and line
  fishing: 'M14 2 L14 12 C14 17 9 19 6 15 M6 15 L8 15',
  // a star
  special: 'M12 3 L14.5 9 L21 9.5 L16 13.8 L17.6 20 L12 16.6 L6.4 20 L8 13.8 L3 9.5 L9.5 9 Z',
  other: 'M12 17 L12 17.5 M12 14 C12 11 15 11 15 8.5 C15 6.5 13.6 5 12 5 C10.4 5 9 6.3 9 8',
}

function MethodIcon({ group = 'other', rare = false, size = 20, style = {}, title }) {
  const hue = GROUP_HUES[group] || GROUP_HUES.other
  const path = PATHS[group] || PATHS.other
  return (
    <svg
      className="method-icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={hue}
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      role="img"
      aria-label={title || group}
      style={{ flexShrink: 0, ...style }}
    >
      <path d={path} />
      {rare && (
        <g className="method-icon__rare" stroke={GROUP_HUES.special} strokeWidth="1.4">
          <path d="M19 2.5 L19 6.5 M17 4.5 L21 4.5" />
          <path d="M4 1.8 L4 4.2 M2.8 3 L5.2 3" />
        </g>
      )}
    </svg>
  )
}

export default MethodIcon
