import { useSyncExternalStore } from 'react'

// 1126px sheet + two 342px gutters. Below this width, panels are drawers,
// never columns competing with the encounter/trainer sheet.
const query = '(min-width: 1820px)'
const hasMatchMedia = () => typeof window !== 'undefined' && typeof window.matchMedia === 'function'
const subscribe = callback => {
  if (!hasMatchMedia()) return () => {}
  const media = window.matchMedia(query)
  media.addEventListener('change', callback)
  return () => media.removeEventListener('change', callback)
}
export default function useDockedPanels() {
  return useSyncExternalStore(subscribe, () => hasMatchMedia() ? window.matchMedia(query).matches : true, () => true)
}
