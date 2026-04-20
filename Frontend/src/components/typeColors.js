// Each type: [background, darkShade]
const TYPE_COLORS = {
  Bug:      ['#ADBD21', '#426B39'],
  Dark:     ['#735A4A', '#4A3931'],
  Dragon:   ['#7B63E7', '#4A3994'],
  Electric: ['#FFC631', '#735218'],
  Fairy:    ['#FECAFE', '#ED8FE7'],
  Fighting: ['#A55239', '#4A3931'],
  Fire:     ['#F75231', '#732108'],
  Flying:   ['#9CADF7', '#425294'],
  Ghost:    ['#6363B5', '#4A3952'],
  Grass:    ['#7BCE52', '#426B39'],
  Ground:   ['#D6B55A', '#735218'],
  Ice:      ['#5ACEE7', '#425294'],
  Normal:   ['#ADA594', '#525252'],
  Poison:   ['#B55AA5', '#4A3952'],
  Psychic:  ['#FF73A5', '#6B3939'],
  Rock:     ['#BDA55A', '#735218'],
  Steel:    ['#ADADC6', '#525252'],
  Water:    ['#399CFF', '#425294'],
}

export function typeBadgeStyle(type) {
  if (!type) return { background: '#555', color: '#fff' }
  const normalized = type.charAt(0).toUpperCase() + type.slice(1).toLowerCase()
  const colors = TYPE_COLORS[normalized]
  if (!colors) return { background: '#555', color: '#fff' }
  const [bg, dark] = colors
  return { background: bg, color: dark, fontWeight: 'bold' }
}

export default TYPE_COLORS
