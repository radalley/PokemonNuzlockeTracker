function Sprite({ speciesId, size = 40, shiny = false, female = false, useIcon = false, alt = '', style }) {
  if (!speciesId) return <div style={{ width: size, height: size, flexShrink: 0 }} />
  const baseFolder = shiny ? 'Shiny' : useIcon ? 'Icons' : 'Standard'
  const src = (female && !useIcon)
    ? `/sprites/${shiny ? 'Shiny' : 'Standard'}/female/${speciesId}.png`
    : `/sprites/${baseFolder}/${speciesId}.png`
  // Fallback chain: female → non-female standard/shiny → useIcon fallback → hidden
  const standardSrc = `/sprites/${shiny ? 'Shiny' : 'Standard'}/${speciesId}.png`
  const iconFallback = useIcon ? `/sprites/Standard/${speciesId}.png` : null
  return (
    <img
      src={src}
      width={size}
      height={size}
      alt={alt}
      style={{ imageRendering: 'pixelated', objectFit: 'contain', flexShrink: 0, ...style }}
      onError={e => {
        const cur = e.currentTarget
        if (female && !useIcon && cur.src !== window.location.origin + standardSrc) {
          cur.src = standardSrc
        } else if (iconFallback && cur.src !== window.location.origin + iconFallback) {
          cur.src = iconFallback
        } else {
          cur.style.visibility = 'hidden'
        }
      }}
    />
  )
}

export default Sprite
