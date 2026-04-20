function formatTypeLabel(type) {
  if (!type) return '???'
  return String(type)
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, character => character.toUpperCase())
}

function getTypeSpriteName(type) {
  if (!type) return 'null'
  const normalized = String(type)
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '_')
    .replace(/[^a-z_]/g, '')

  return normalized || 'null'
}

function TypeIcon({ type = null, height = 18, width = 'auto', style = {}, title }) {
  const label = formatTypeLabel(type)
  const spriteName = getTypeSpriteName(type)

  return (
    <img
      src={`/sprites/types/${spriteName}.png`}
      alt={label}
      title={title || label}
      style={{
        height,
        width,
        objectFit: 'contain',
        imageRendering: 'pixelated',
        flexShrink: 0,
        ...style,
      }}
      onError={event => {
        if (!event.currentTarget.src.endsWith('/null.png')) {
          event.currentTarget.src = '/sprites/types/null.png'
        }
      }}
    />
  )
}

export function TypeIconRow({ types = [], height = 18, gap = 4, placeholder = false, style = {}, justifyContent = 'flex-start' }) {
  const resolvedTypes = types.filter(Boolean)
  const icons = resolvedTypes.length > 0 ? resolvedTypes : (placeholder ? [null] : [])

  if (icons.length === 0) return null

  return (
    <div style={{ display: 'flex', gap, flexWrap: 'wrap', alignItems: 'center', justifyContent, ...style }}>
      {icons.map((type, index) => (
        <TypeIcon key={`${type || 'null'}-${index}`} type={type} height={height} />
      ))}
    </div>
  )
}

export default TypeIcon