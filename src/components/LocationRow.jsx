

import { useState, useEffect } from 'react'

function LocationRow({ row, gameId }) {
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

  /*added*/
  const [trainerParties, setTrainerParties] = useState({})

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

  return (
    <div>
      <p>{row.display_name}</p>
      <p>Encounters: {pool.map(p => p.name.charAt(0).toUpperCase() + p.name.slice(1).toLowerCase()).join(', ')}</p>

      {trainers.length > 0 && (
        <>
          <button onClick={() => setTrainersOpen(!trainersOpen)}>
            {trainersOpen ? 'Hide Trainers' : 'Show Trainers'}
          </button>
          {trainersOpen && (
            <div>

              {/* {trainers.map(t => (
                <div key={t.trainer_id}>
                  <p onClick={() => {
                    setSelectedTrainer(t.trainer_id)
                    fetch(`http://localhost:5000/api/trainer-party/${t.trainer_name}`)
                      .then(res => res.json())
                      .then(data => setTrainerParty(data))
                  }}>{t.trainer_name}</p>
                  {selectedTrainer === t.trainer_id && (
                    <div>
                      {trainerParty.map((p, i) => (
                        <p key={i}>{p.species_name} | Lv.{p.lvl} | IV: {p.iv}</p>
                      ))}
                    </div>
                  )}
                </div>
              ))} */}

              {trainers.map(t => (
                <div key={t.trainer_id}>
                  <p>{t.trainer_name}</p>
                  {(trainerParties[t.trainer_name] || []).map((p, i) => (
                    <p key={i}>{p.species_name} | Lv.{p.lvl}</p>
                  ))}
                </div>
              ))}



            </div>
          )}
        </>
      )}

    </div>

  )
}

export default LocationRow