import { useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'

function NewRun() {
    const navigate = useNavigate()
    const [gameid, setGameId] = useState('')
    const [runName, setRunName] = useState('')
    const [games, setGames] = useState([])

    useEffect(() => {
    fetch('http://localhost:5000/api/games')
      .then(res => res.json())
      .then(data => setGames(data))
    }, [])

function handleCreate() {
  if (!gameid || !runName) {
    alert('Please select a game and enter a run name')
    return
  }

  fetch('http://localhost:5000/api/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ game_id: gameid, run_name: runName })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        navigate(`/attempt/${data.run_id}`)
      }
    })
}

  return (
    <div>
      <p>Game ID: {gameid}</p>
      <p>Run Name: {runName}</p>
      <h1>New Run</h1>
       <select value={gameid} onChange={(e) => setGameId(e.target.value)}>
        <option value="">Select a game...</option>
        {games.map(g => (
          <option key={g.game_id} value={g.game_id}>
            Pokemon {g.name} (Gen {g.generation})
          </option>
        ))}
      </select>
      <input 
        type="text" 
        placeholder="Run name" 
        value={runName}
        onChange={(e) => setRunName(e.target.value)}
        />
      <button onClick={handleCreate}>Create</button>
      <button onClick={ () => navigate('/')}> Back </button> 
    </div>
  )
}



export default NewRun