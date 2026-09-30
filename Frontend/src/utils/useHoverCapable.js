import { useSyncExternalStore } from 'react'

const HOVER_QUERY = '(hover: hover) and (pointer: fine)'

function hasMatchMedia() {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
}

function subscribe(onChange) {
  if (!hasMatchMedia()) return () => {}
  const query = window.matchMedia(HOVER_QUERY)
  // Safari < 14 only has the deprecated listener API.
  if (typeof query.addEventListener === 'function') {
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }
  query.addListener(onChange)
  return () => query.removeListener(onChange)
}

// Defaults to true where matchMedia is unavailable (jsdom, SSR) so the
// desktop behaviour is what tests and non-browser renders see.
function getSnapshot() {
  return hasMatchMedia() ? window.matchMedia(HOVER_QUERY).matches : true
}

function getServerSnapshot() {
  return true
}

// Menus that open on mouseenter are a trap on touch: iOS synthesises a
// hover before the click, so the first tap opens the menu and the click
// that follows immediately toggles it shut — the menu looks dead until
// you tap twice. Gate the hover affordance on a real pointer and leave
// click as the sole path on touch.
export default function useHoverCapable() {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}
