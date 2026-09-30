// Helpers for a split's curated item library, shared by the timeline
// panel and the split sections.

export const titleCase = text => String(text || '').toLowerCase().replace(/\b\w/g, c => c.toUpperCase())

export const spriteName = text => String(text || '').toLowerCase().replace(/^item_/, '').replace(/[ _]+/g, '-').replace(/[^a-z0-9-]/g, '')

export const itemGroups = [
  ['thief', 'Thief'], ['dust_cloud', 'Dust clouds'], ['conditional', 'Conditional'], ['manual', 'Other']
]

export const sourcesFor = item => item.sources?.length ? item.sources : [{ method_kind: 'manual', source_detail: item.method }]

export const chanceLabel = sources => {
  const values = [...new Set(sources.map(source => Number(source.chance_percent)).filter(Number.isFinite))].sort((a, b) => a - b)
  if (!values.length) return ''
  return values.length === 1 ? `${values[0]}%` : `${values[0]}–${values.at(-1)}%`
}

/** "68 items · Thief 43 · Dust clouds 28" for a collapsed summary. */
export function itemSummary(items) {
  if (!items?.length) return 'No items recorded'
  const counts = itemGroups
    .map(([key, label]) => [label, items.filter(item => sourcesFor(item).some(source => source.method_kind === key)).length])
    .filter(([, n]) => n > 0)
  return [`${items.length} item${items.length === 1 ? '' : 's'}`, ...counts.map(([label, n]) => `${label} ${n}`)].join(' · ')
}
