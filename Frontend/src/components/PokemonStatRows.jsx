const NATURES = [
  { name: 'Adamant', up: 'Atk', down: 'SpA' },
  { name: 'Bashful', up: null, down: null },
  { name: 'Bold', up: 'Def', down: 'Atk' },
  { name: 'Brave', up: 'Atk', down: 'Spe' },
  { name: 'Calm', up: 'SpD', down: 'Atk' },
  { name: 'Careful', up: 'SpD', down: 'SpA' },
  { name: 'Docile', up: null, down: null },
  { name: 'Gentle', up: 'SpD', down: 'Def' },
  { name: 'Hardy', up: null, down: null },
  { name: 'Hasty', up: 'Spe', down: 'Def' },
  { name: 'Impish', up: 'Def', down: 'SpA' },
  { name: 'Jolly', up: 'Spe', down: 'SpA' },
  { name: 'Lax', up: 'Def', down: 'SpD' },
  { name: 'Lonely', up: 'Atk', down: 'Def' },
  { name: 'Mild', up: 'SpA', down: 'Def' },
  { name: 'Modest', up: 'SpA', down: 'Atk' },
  { name: 'Naive', up: 'Spe', down: 'SpD' },
  { name: 'Naughty', up: 'Atk', down: 'SpD' },
  { name: 'Quiet', up: 'SpA', down: 'Spe' },
  { name: 'Quirky', up: null, down: null },
  { name: 'Rash', up: 'SpA', down: 'SpD' },
  { name: 'Relaxed', up: 'Def', down: 'Spe' },
  { name: 'Sassy', up: 'SpD', down: 'Spe' },
  { name: 'Serious', up: null, down: null },
  { name: 'Timid', up: 'Spe', down: 'Atk' },
]

export const POKEMON_STAT_ROWS = [
  { key: 'hp', label: 'HP' },
  { key: 'atk', label: 'Atk' },
  { key: 'def', label: 'Def' },
  { key: 'spa', label: 'SpA' },
  { key: 'spd', label: 'SpD' },
  { key: 'spe', label: 'Spe' },
]

function getNatureDetails(nature) {
  return NATURES.find(entry => entry.name === nature) || null
}

function getNatureModifierForStat(nature, statLabel) {
  const selectedNature = getNatureDetails(nature)
  if (!selectedNature || !selectedNature.up || !selectedNature.down) return null
  if (selectedNature.up === statLabel) return { text: '+10%', color: '#e55' }
  if (selectedNature.down === statLabel) return { text: '-10%', color: '#66a8ff' }
  return null
}

function getNatureAdjustedStatValue(nature, statLabel, value) {
  if (value == null) return null
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) return null

  const modifier = getNatureModifierForStat(nature, statLabel)
  if (!modifier) return numericValue
  if (modifier.text === '+10%') return Math.round(numericValue * 1.1)
  if (modifier.text === '-10%') return Math.round(numericValue * 0.9)
  return numericValue
}

function getStatBarColor(value) {
  if (value == null) return '#3a4050'
  if (value <= 50) return '#e55'
  if (value <= 80) return '#e98b3a'
  if (value <= 100) return '#d4c02a'
  if (value <= 120) return '#8ccf3f'
  return '#5ba85b'
}

function getScaleStat(stats, nature, rows) {
  return Math.max(
    150,
    ...rows.map(row => {
      const baseValue = Number(stats?.[row.key]) || 0
      const adjustedValue = getNatureAdjustedStatValue(nature, row.label, baseValue) || 0
      return Math.max(baseValue, adjustedValue)
    })
  )
}

function getComparisonScaleStat(leftStats, leftNature, rightStats, rightNature, rows) {
  return Math.max(
    150,
    ...rows.map(row => {
      const leftBaseValue = Number(leftStats?.[row.key]) || 0
      const rightBaseValue = Number(rightStats?.[row.key]) || 0
      const leftAdjustedValue = getNatureAdjustedStatValue(leftNature, row.label, leftBaseValue) || 0
      const rightAdjustedValue = getNatureAdjustedStatValue(rightNature, row.label, rightBaseValue) || 0

      return Math.max(leftBaseValue, leftAdjustedValue, rightBaseValue, rightAdjustedValue)
    })
  )
}

function formatGridSize(value) {
  if (value == null) return null
  if (typeof value === 'number') return `${value}px`
  return value
}

function PokemonStatRows({
  stats,
  compareStats = null,
  nature = '',
  compareNature = '',
  rows = POKEMON_STAT_ROWS,
  rowGap = '8px',
  columnGap = '8px',
  labelColumnWidth = 98,
  labelTextWidth = 28,
  modifierWidth = 38,
  valueColumnWidth = 32,
  barHeight = 8,
  labelFontSize = '0.72em',
  valueFontSize = '0.75em',
  labelGap = '4px',
  trackColor = '#252c38',
  reserveModifierSpace = true,
  showNatureModifierText = true,
  colorNatureModifiedLabel = false,
  rowGridTemplateColumns = null,
  style = {},
}) {
  if (compareStats) {
    const scaleStat = getComparisonScaleStat(stats, nature, compareStats, compareNature, rows)
    const innerBarHeight = Math.max(2, barHeight - 2)
    const innerBarTop = Math.floor((barHeight - innerBarHeight) / 2)

    return (
      <div style={{ display: 'grid', gap: rowGap, ...style }}>
        {rows.map(row => {
          const leftValue = stats?.[row.key]
          const rightValue = compareStats?.[row.key]
          const leftAdjustedValue = getNatureAdjustedStatValue(nature, row.label, leftValue)
          const rightAdjustedValue = getNatureAdjustedStatValue(compareNature, row.label, rightValue)
          const leftHasAdvantage = leftAdjustedValue != null && rightAdjustedValue != null && leftAdjustedValue > rightAdjustedValue
          const rightHasAdvantage = leftAdjustedValue != null && rightAdjustedValue != null && rightAdjustedValue > leftAdjustedValue
          const leftDisplayValue = leftValue ?? '—'
          const rightDisplayValue = rightValue ?? '—'
          const leftWidthPct = leftAdjustedValue != null ? Math.min(100, Math.round((leftAdjustedValue / scaleStat) * 100)) : 0
          const rightWidthPct = rightAdjustedValue != null ? Math.min(100, Math.round((rightAdjustedValue / scaleStat) * 100)) : 0

          return (
            <div
              key={row.key}
              style={{
                display: 'grid',
                gridTemplateColumns: `minmax(0, 1fr) ${valueColumnWidth}px 6px ${labelColumnWidth}px 6px ${valueColumnWidth}px minmax(0, 1fr)`,
                columnGap,
                alignItems: 'center',
              }}
            >
              <div style={{ position: 'relative', height: `${barHeight}px`, background: trackColor, borderRadius: '999px', overflow: 'hidden' }}>
                <div
                  style={{
                    position: 'absolute',
                    right: 0,
                    top: `${innerBarTop}px`,
                    width: `${leftWidthPct}%`,
                    height: `${innerBarHeight}px`,
                    background: getStatBarColor(leftAdjustedValue),
                    borderRadius: '999px'
                  }}
                />
              </div>
              <span style={{ fontSize: valueFontSize, color: '#eef2f7', textAlign: 'right', whiteSpace: 'nowrap' }}>{leftDisplayValue}</span>
              <span style={{ fontSize: valueFontSize, color: leftHasAdvantage ? '#5ba85b' : 'transparent', textAlign: 'center', fontWeight: 'bold', lineHeight: 1 }}>
                ^
              </span>
              <span style={{ fontSize: labelFontSize, color: '#9ca0ad', textAlign: 'center', whiteSpace: 'nowrap' }}>{row.label}</span>
              <span style={{ fontSize: valueFontSize, color: rightHasAdvantage ? '#5ba85b' : 'transparent', textAlign: 'center', fontWeight: 'bold', lineHeight: 1 }}>
                ^
              </span>
              <span style={{ fontSize: valueFontSize, color: '#eef2f7', textAlign: 'left', whiteSpace: 'nowrap' }}>{rightDisplayValue}</span>
              <div style={{ position: 'relative', height: `${barHeight}px`, background: trackColor, borderRadius: '999px', overflow: 'hidden' }}>
                <div
                  style={{
                    position: 'absolute',
                    left: 0,
                    top: `${innerBarTop}px`,
                    width: `${rightWidthPct}%`,
                    height: `${innerBarHeight}px`,
                    background: getStatBarColor(rightAdjustedValue),
                    borderRadius: '999px'
                  }}
                />
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  const scaleStat = getScaleStat(stats, nature, rows)
  const innerBarHeight = Math.max(2, barHeight - 2)
  const innerBarTop = Math.floor((barHeight - innerBarHeight) / 2)

  return (
    <div style={{ display: 'grid', gap: rowGap, ...style }}>
      {rows.map(row => {
        const value = stats?.[row.key]
        const widthPct = value != null ? Math.min(100, Math.round((value / scaleStat) * 100)) : 0
        const natureModifier = getNatureModifierForStat(nature, row.label)
        const adjustedValue = getNatureAdjustedStatValue(nature, row.label, value)
        const adjustedWidthPct = adjustedValue != null ? Math.min(100, Math.round((adjustedValue / scaleStat) * 100)) : 0
        const deltaLeftPct = Math.min(widthPct, adjustedWidthPct)
        const deltaWidthPct = Math.max(0, Math.abs(adjustedWidthPct - widthPct))
        const showModifierSlot = showNatureModifierText && (reserveModifierSpace || Boolean(natureModifier))
        const effectiveModifierWidth = showModifierSlot ? modifierWidth : 0
        const effectiveLabelGap = showModifierSlot ? labelGap : 0
        const labelColor = colorNatureModifiedLabel && natureModifier ? natureModifier.color : '#9ca0ad'
        const gridTemplateColumns = rowGridTemplateColumns || `${formatGridSize(labelColumnWidth)} ${formatGridSize(valueColumnWidth)} minmax(0, 1fr)`
        const labelTextWidthValue = formatGridSize(labelTextWidth) || 'auto'
        const modifierWidthValue = formatGridSize(effectiveModifierWidth) || '0px'

        return (
          <div key={row.key} style={{ display: 'grid', gridTemplateColumns, columnGap, alignItems: 'center' }}>
            <span style={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'center', gap: effectiveLabelGap, whiteSpace: 'nowrap' }}>
              <span style={{ width: labelTextWidthValue, fontSize: labelFontSize, color: labelColor, textAlign: 'left' }}>{row.label}</span>
              <span style={{ width: modifierWidthValue, fontSize: labelFontSize, color: natureModifier?.color || 'transparent', textAlign: 'left', overflow: 'hidden' }}>
                {showNatureModifierText ? (natureModifier?.text || '+10%') : ''}
              </span>
            </span>
            <span style={{ fontSize: valueFontSize, color: '#eef2f7', textAlign: 'right', whiteSpace: 'nowrap' }}>{value ?? '—'}</span>
            <div style={{ position: 'relative', height: `${barHeight}px`, background: trackColor, borderRadius: '999px', overflow: 'hidden' }}>
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  top: `${innerBarTop}px`,
                  width: `${widthPct}%`,
                  height: `${innerBarHeight}px`,
                  background: getStatBarColor(value),
                  borderRadius: '999px'
                }}
              />
              {natureModifier && deltaWidthPct > 0 && (
                <div
                  style={{
                    position: 'absolute',
                    left: `${deltaLeftPct}%`,
                    top: `${innerBarTop}px`,
                    width: `${deltaWidthPct}%`,
                    height: `${innerBarHeight}px`,
                    background: natureModifier.color,
                    opacity: 0.45,
                    borderRadius: '999px'
                  }}
                />
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default PokemonStatRows