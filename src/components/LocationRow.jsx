

import { useState, useEffect, useRef } from 'react'

function LocationRow({ row, gameId }) {
  const rootRef = useRef(null)
  const [pool, setPool] = useState([])

  useEffect(() => {
    fetch(`http://localhost:5000/api/encounter-pool/${row.event_id}?game_id=${gameId}`)
      .then(res => res.json())
      .then(data => setPool(data))
  }, [gameId])

  const [trainers, setTrainers] = useState([])
  const [trainersOpen, setTrainersOpen] = useState(false)
  const [selectedTrainer, setSelectedTrainer] = useState(null)
  const [trainerParty, setTrainerParty] = useState([])
  const [trainerParties, setTrainerParties] = useState({})

  /* added for encounter logic*/
  const [encounter, setEncounter] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [showSearch, setShowSearch] = useState(false)

  const [nickname, setNickname] = useState('')
  const [nature, setNature] = useState('')
  const [status, setStatus] = useState('')
  const [isShiny, setIsShiny] = useState(false)

  const [expandedTrainer, setExpandedTrainer] = useState(null)

  useEffect(() => {
    fetch(`http://localhost:5000/api/trainer-list/${row.event_id}`)
      .then(res => res.json())
      .then(data => setTrainers(data))
  }, [])

  useEffect(() => {
    if (!trainersOpen || trainers.length === 0) return
    trainers.forEach(t => {
      fetch(`http://localhost:5000/api/trainer-party/${t.trainer_name}`)
        .then(res => res.json())
        .then(data => setTrainerParties(prev => ({ ...prev, [t.trainer_name]: data })))
    })
  }, [trainersOpen])

  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults(pool)
      return
    }
    const timer = setTimeout(() => {
      fetch(`http://localhost:5000/api/species/search?q=${searchQuery}`)
        .then(res => res.json())
        .then(data => setSearchResults(data))
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (rootRef.current && !rootRef.current.contains(event.target)) {
        setShowSearch(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
  fetch(`http://localhost:5000/api/encounter-pool/${row.event_id}?game_id=${gameId}`)
    .then(res => res.json())
    .then(data => {
      setPool(data)
      setSearchResults(data)
    })
}, [gameId])

  return (

    <div ref={rootRef}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        <div style={{ minWidth: '150px', fontWeight: 'bold' }}>{row.display_name}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', position: 'relative' }}>
          <div style={{ display: 'flex', flexDirection: 'column', minWidth: '180px', position: 'relative' }}>
            <input
              type="text"
              placeholder="Encounter"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value)
                setEncounter(null)
                setShowSearch(true)
              }}
              onFocus={() => setShowSearch(true)}
              style={{ width: '180px' }}
            />

            {showSearch && searchResults.length > 0 && (
              <div style={{ position: 'absolute', top: '36px', left: 0, right: 0, maxHeight: '160px', overflowY: 'auto', background: '#fff', border: '1px solid #ccc', zIndex: 1000 }}>
                {searchResults.map(s => (
                  <div
                    key={s.species_id}
                    onClick={() => {
                      setEncounter(s)
                      setSearchQuery(s.name)
                      setShowSearch(false)
                    }}
                    style={{ padding: '6px 8px', cursor: 'pointer', borderBottom: '1px solid #eee' }}
                  >
                    {s.name}
                  </div>
                ))}
              </div>
            )}
          </div>

          <input
            type="text"
            placeholder="Nickname"
            value={nickname}
            onChange={e => setNickname(e.target.value)}
            style={{ minWidth: '150px' }}
          />

          <select value={nature} onChange={e => setNature(e.target.value)} style={{ minWidth: '120px' }}>
            <option value="">Nature</option>
            <option value="Adamant">Adamant</option>
            <option value="Bold">Bold</option>
            <option value="Modest">Modest</option>
            <option value="Timid">Timid</option>
            <option value="Jolly">Jolly</option>
            <option value="Calm">Calm</option>
          </select>

          <select value={status} onChange={e => setStatus(e.target.value)} style={{ minWidth: '120px' }}>
            <option value="">Status</option>
            <option value="captured">Captured</option>
            <option value="missed">Missed</option>
            <option value="dead">Dead</option>
          </select>

          <label style={{ display: 'flex', alignItems: 'center' }}>
            <input
              type="checkbox"
              checked={isShiny}
              onChange={e => setIsShiny(e.target.checked)}
              style={{ marginRight: '4px' }}
            />
            Shiny
          </label>
        </div>
      </div>

      <div style={{ marginLeft: '170px' }}>
        {trainers.filter(t => !t.is_event).length > 0 && (
          <>
            <button onClick={() => setTrainersOpen(!trainersOpen)}>
              {trainersOpen ? 'Hide Trainers' : 'Show Trainers'}
            </button>
            {trainersOpen && (
              <div>
                {trainers.filter(t => !t.is_event).map(t => (
                  <div key={t.trainer_id} style={{ border: '1px solid #ccc', margin: '4px 0', padding: '8px', cursor: 'pointer' }}>
                    <div
                      style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                      onClick={() => setExpandedTrainer(expandedTrainer === t.trainer_name ? null : t.trainer_name)}
                    >
                      <div style={{ fontWeight: 'bold' }}>{t.trainer_name}</div>
                      <div>
                        {(trainerParties[t.trainer_name] || []).map((p, i) => (
                          <span key={i} style={{ marginRight: '8px' }}>{p.species_name}</span>
                        ))}
                      </div>
                    </div>
                    {expandedTrainer === t.trainer_name && (
                      <div style={{ marginTop: '8px', display: 'grid', gridTemplateColumns: `repeat(${(trainerParties[t.trainer_name] || []).length}, 1fr)`, gap: '16px' }}>
                        {(trainerParties[t.trainer_name] || []).map((p, i) => {
                          const movesList = p.moves ? p.moves.split(',').map(m => m.trim().replace('MOVE_', '')) : []
                          return (
                            <div key={i} style={{ borderLeft: '1px solid #ddd', paddingLeft: '8px' }}>
                              <div style={{ fontWeight: 'bold' }}>{p.species_name}</div>
                              <div>Lvl {p.lvl}</div>
                              {movesList.length > 0 && (
                                movesList.map((move, idx) => (
                                  <div key={idx} style={{ fontSize: '0.85em', color: '#666' }}>{move}</div>
                                ))
                              )}
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

    </div>

  )
}

export default LocationRow