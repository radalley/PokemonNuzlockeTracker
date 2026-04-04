
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useNavigate } from 'react-router-dom'
import LocationRow from '../components/LocationRow'
import BossRow from '../components/BossRow'
import RivalRow from '../components/RivalRow'

function Attempt() {
  const { runId, attemptId } = useParams()
  const navigate = useNavigate()
  const [script, setScript] = useState([])
  const [runDetails, setRunDetails] = useState(null)
  const [currentStarter, setCurrentStarter] = useState('')

  useEffect(() => {
    if (runDetails?.starter) {
      setCurrentStarter(runDetails.starter)
    }
  }, [runDetails])

  const handleStarterChange = (newStarter) => {
    if (newStarter !== currentStarter) {
      fetch(`http://localhost:5000/api/update-starter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: runId, attempt_id: attemptId, starter: newStarter })
      })
      .then(res => res.json())
      .then(() => {
        setCurrentStarter(newStarter)
        setRunDetails(prev => ({ ...prev, starter: newStarter }))
      })
      .catch(err => console.error('Failed to update starter:', err))
    }
  }
  useEffect(() => {
    fetch(`http://localhost:5000/api/runs/${runId}/${attemptId}`)
      .then(res => res.json())
      .then(data => setRunDetails(data))
  }, [runId, attemptId])
useEffect(() => {
  if (!runDetails?.starter) return
  fetch(`http://localhost:5000/api/script?starter=${runDetails.starter}`)
    .then(res => res.json())
    .then(data => setScript(data))
}, [runDetails])

  if (!runDetails) return <p>Loading...</p>

  function renderScriptRow(row) {
    console.log(row.event_type)
    if (row.event_type === 'Location') return <LocationRow key={row.sort_order} row={row} gameId={runDetails?.game_id} />
    if (row.event_type === 'Rival') return <RivalRow key={row.sort_order} row={row} />
    return <BossRow key={row.sort_order} row={row} />
  }

  return (
    <div style={{ paddingTop: '80px', paddingBottom: '40px' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px', borderBottom: '1px solid #ccc', position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1000, backgroundColor: '#16171d' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ width: '50px', height: '50px', backgroundColor: '', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Game Art</div>
          <div>
            <div style={{ fontWeight: 'bold' }}>{runDetails?.game_name || 'Game Name'}</div>
            <div>{runDetails?.run_name || 'Run Name'}</div>
          </div>
          <button onClick={() => navigate('/')}>Main Menu</button>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} style={{ width: '50px', height: '50px', backgroundColor: '', border: '1px solid #ccc', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              Party {i + 1}
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          {/* <button>Pokebank</button> */}
          <button>Box</button>
          <button>Graveyard</button>
        </div>
      </header>

      <div style={{ textAlign: 'left' }}>
        <p>Starter: {currentStarter}</p>
        <div style={{ display: 'flex', gap: '10px', marginTop: '5px' }}>
          <button 
            onClick={() => handleStarterChange('Fire')}
            style={{ 
              padding: '4px 8px', 
              backgroundColor: currentStarter === 'Fire' ? '#ff6b6b' : '',
              border: '1px solid #ccc',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Fire
          </button>
          <button 
            onClick={() => handleStarterChange('Grass')}
            style={{ 
              padding: '4px 8px', 
              backgroundColor: currentStarter === 'Grass' ? '#51cf66' : '',
              border: '1px solid #ccc',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Grass
          </button>
          <button 
            onClick={() => handleStarterChange('Water')}
            style={{ 
              padding: '4px 8px', 
              backgroundColor: currentStarter === 'Water' ? '#74c0fc' : '',
              border: '1px solid #ccc',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Water
          </button>
        </div>
      </div>

      {script.map(row => renderScriptRow(row))}

      <footer style={{ position: 'fixed', bottom: 0, left: 0, right: 0, height: '40px', borderTop: '1px solid #ccc', backgroundColor: '#16171d', zIndex: 1000, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '10px' }}>
        <button>Game Documentation</button>
        <button>Contact/About Me</button>
      </footer>
    </div>
  )
}

export default Attempt