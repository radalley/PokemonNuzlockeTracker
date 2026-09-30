// Multi-battle formats a fight can use. Single battles carry no marker.
export const BATTLE_FORMATS = {
  double: { color: '#7ec8e3', rgb: '126, 200, 227', label: 'Double', pips: 2 },
  triple: { color: '#f2b46b', rgb: '242, 180, 107', label: 'Triple', pips: 3 },
  rotation: { color: '#b48ce3', rgb: '180, 140, 227', label: 'Rotation', pips: 0 },
}

export function normalizeBattleFormat(value) {
  const key = String(value || '').trim().toLowerCase()
  return BATTLE_FORMATS[key] ? key : null
}
