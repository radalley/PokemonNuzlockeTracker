import { useEffect, useRef, useState } from 'react'
import Sprite from './Sprite'
import { apiFetch } from '../utils/api'
import { getLocalFeedPokemon, hasLocalData } from '../utils/guestStorage'
import { useAuth } from '../contexts/AuthContext'

// px per second the feed scrolls upward
const DEFAULT_SPEED = 40
const DEFAULT_COLUMNS = 8
const ROW_GAP_PX = 8
const ROW_PAD_X_PX = 12
const ROW_PAD_Y_PX = 6
const MIN_SPRITE_SIZE = 24
const USER_FEED_LIMIT = 100
const DEFAULT_FEED_LIMIT = 300

function parseBadgeIds(value) {
  if (value == null) return []
  if (Array.isArray(value)) {
    return value
      .map(Number)
      .filter(Number.isFinite)
      .sort((a, b) => a - b)
  }
  if (typeof value === 'number') {
    return Number.isFinite(value) ? [value] : []
  }

  const text = String(value).trim()
  if (!text) return []

  // Support JSON array payloads and comma-separated badge IDs.
  if (text.startsWith('[') && text.endsWith(']')) {
    try {
      const parsed = JSON.parse(text)
      if (Array.isArray(parsed)) {
        return parsed.map(Number).filter(Number.isFinite).sort((a, b) => a - b)
      }
    } catch {
    }
  }

  return text
    .split(',')
    .map(part => Number(part.trim()))
    .filter(Number.isFinite)
    .sort((a, b) => a - b)
}

function shuffleList(items) {
  const copy = [...items]
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    const temp = copy[i]
    copy[i] = copy[j]
    copy[j] = temp
  }
  return copy
}

function PokemonFeed({ speed = DEFAULT_SPEED, columns = DEFAULT_COLUMNS, className = '' }) {
  const { user, loading: authLoading } = useAuth()
  const [species, setSpecies] = useState([])
  const [spriteSize, setSpriteSize] = useState(40)
  const feedRef = useRef(null)
  const containerRef = useRef(null)
  const firstGroupRef = useRef(null)
  const loopHeightRef = useRef(0)
  const offsetRef = useRef(0)
  const rafRef = useRef(null)
  const lastTimeRef = useRef(null)

  useEffect(() => {
    // Wait until auth has resolved so we know whether to use the authed
    // Pokebank route or fall back to guest storage.
    if (authLoading) return

    let cancelled = false

    async function loadFeed() {
      let userData = []

      // 1. Try authenticated server-side Pokebank
      if (user) {
        try {
          const userResponse = await apiFetch(`/api/pokebank/random-feed?limit=${USER_FEED_LIMIT}`)
          if (userResponse.ok) {
            const parsed = await userResponse.json()
            if (Array.isArray(parsed) && parsed.length > 0) {
              userData = parsed.map(item => ({ ...item, fromUser: true }))
            }
          }
        } catch {
        }
      }

      // 2. If not signed in, fall back to local guest storage
      if (userData.length === 0 && hasLocalData()) {
        const local = getLocalFeedPokemon()
        userData = local.slice(0, USER_FEED_LIMIT)
      }

      const remainingDefault = Math.max(0, DEFAULT_FEED_LIMIT - userData.length)

      try {
        let defaultData = []
        if (remainingDefault > 0) {
          const response = await fetch(`/api/species/random-feed?limit=${remainingDefault}`)
          const data = await response.json()
          defaultData = Array.isArray(data) ? data : []
        }

        if (!cancelled) {
          setSpecies(shuffleList([...userData, ...defaultData]))
        }
      } catch {
        if (!cancelled) {
          setSpecies(shuffleList(userData))
        }
      }
    }

    loadFeed()
    return () => {
      cancelled = true
    }
  }, [authLoading, user])

  useEffect(() => {
    const feed = feedRef.current
    if (!feed) return

    function measure() {
      const width = feed.clientWidth
      const usable = width - (ROW_PAD_X_PX * 2) - (ROW_GAP_PX * (columns - 1))
      const nextSize = Math.max(MIN_SPRITE_SIZE, Math.floor(usable / columns))
      setSpriteSize(nextSize)
    }

    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(feed)
    return () => observer.disconnect()
  }, [columns, species.length])

  // Build rows of N columns from the species list
  const rows = []
  for (let i = 0; i < species.length; i += columns) {
    const slice = species.slice(i, i + columns)
    if (slice.length === 0) continue
    // Keep each row full width by wrapping from the start when needed.
    if (slice.length < columns) {
      let refillIndex = 0
      while (slice.length < columns && species.length > 0) {
        slice.push(species[refillIndex % species.length])
        refillIndex += 1
      }
    }
    rows.push(slice)
  }

  // Measure the first group's actual rendered height after rows are painted
  useEffect(() => {
    if (firstGroupRef.current) {
      loopHeightRef.current = firstGroupRef.current.offsetHeight
    }
  }, [rows.length])

  useEffect(() => {
    if (rows.length === 0) return
    const container = containerRef.current
    if (!container) return

    offsetRef.current = 0

    function tick(timestamp) {
      if (lastTimeRef.current === null) lastTimeRef.current = timestamp
      const delta = (timestamp - lastTimeRef.current) / 1000
      lastTimeRef.current = timestamp

      offsetRef.current += speed * delta
      const loopAt = loopHeightRef.current
      if (loopAt > 0 && offsetRef.current >= loopAt) {
        offsetRef.current -= loopAt
      }

      if (container) {
        container.style.transform = `translateY(-${offsetRef.current}px)`
      }

      rafRef.current = requestAnimationFrame(tick)
    }

    rafRef.current = requestAnimationFrame(tick)
    return () => {
      cancelAnimationFrame(rafRef.current)
      lastTimeRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows.length, speed])

  const renderRows = (keyPrefix) =>
    rows.map((row, rowIdx) => (
      <div
        key={`${keyPrefix}-${rowIdx}`}
        className="pokemon-feed__row"
        style={{ gap: `${ROW_GAP_PX}px`, padding: `${ROW_PAD_Y_PX}px ${ROW_PAD_X_PX}px` }}
      >
        {row.map((s, idx) => {
          const isDead = String(s.status || '').toLowerCase() === 'dead'
          const isUser = Boolean(s.fromUser)
          const badgeIds = parseBadgeIds(s.badges_earned)
          const classes = ['pokemon-feed__sprite']
          if (isDead) classes.push('is-dead')
          if (isUser) classes.push('is-user')

          return (
            <div
              key={`${s.species_id}-${idx}`}
              className={classes.join(' ')}
              style={{ width: `${spriteSize}px`, height: `${spriteSize}px` }}
            >
              <Sprite speciesId={s.species_id} size={spriteSize} shiny={Boolean(s.shiny)} />
              {badgeIds.length > 0 && (
                <div className="pokemon-feed__badge-strip" aria-hidden="true">
                  {badgeIds.map(badgeId => (
                    <img
                      key={badgeId}
                      className="pokemon-feed__badge"
                      src={`/sprites/Badges/${badgeId}.png`}
                      alt=""
                    />
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    ))

  return (
    <div className={`pokemon-feed ${className}`.trim()} ref={feedRef}>
      <div className="pokemon-feed__inner" ref={containerRef}>
        {rows.length > 0 && (
          <>
            <div ref={firstGroupRef}>
              {renderRows('a')}
            </div>
            <div>
              {renderRows('b')}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default PokemonFeed
