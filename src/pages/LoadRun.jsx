import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

function LoadRun() {
  const navigate = useNavigate()
  const [runs, setRuns] = useState([])

  useEffect(() => {
    fetch('http://localhost:5000/api/runs')
      .then(res => res.json())
      .then(data => setRuns(data))
  }, [])

  return (
    <div>
      <div style={{ padding: '10px', textAlign: 'center' }}>
        <button onClick={() => navigate('/')}>Main Menu</button>
      </div>
      <h1>Load Run</h1>
      <table>
        <thead>
          <tr>
            <th>Run Name</th>
            <th>Game</th>
            <th>Attempts</th>
            <th>Created</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {runs.map(r => (
            <tr key={r.run_id}>
              <td>{r.run_name}</td>
              <td>Pokemon {r.name}</td>
              <td>{r.total_attempts}</td>
              <td>{r.created_at}</td>
              <td>
                <button onClick={() => navigate(`/attempt/${r.run_id}/${r.latest_attempt}`)}>
                  Load
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button onClick={() => navigate('/')}>Back</button>
    </div>
  )
}

export default LoadRun