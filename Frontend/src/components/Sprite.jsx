function Sprite({ speciesId, size = 1040, shiny = false, useIcon = false, alt = '' }) {
  if (!speciesId) return <div style={{ width: size, height: size, flexShrink: 0 }} />
  const folder = shiny ? 'Shiny' : useIcon ? 'Icons' : 'Standard'
  return (
    <img
      src={`/sprites/${folder}/${speciesId}.png`}
      width={size}
      height={size}
      alt={alt}
      style={{ imageRendering: 'pixelated', objectFit: 'contain', flexShrink: 0 }}
      onError={e => { e.currentTarget.style.visibility = 'hidden' }}
    />
  )
}

export default Sprite
