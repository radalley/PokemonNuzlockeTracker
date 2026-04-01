// import { useNavigate } from 'react-router-dom'

// function Attempt() {
//     const navigate = useNavigate()

//   return (
//     <div>
//         <p>test of attempt screen</p>
//       <h1>Attempt</h1>
//       <button onClick={ () => navigate('/')}> Home </button> 
//     </div>
//   )
// }

// export default Attempt

import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useNavigate } from 'react-router-dom'
import LocationRow from '../components/LocationRow'
import BossRow from '../components/BossRow'
import RivalRow from '../components/RivalRow'

function Attempt() {
  const { runId } = useParams()
  const navigate = useNavigate()
  const [script, setScript] = useState([])
  const [runDetails, setRunDetails] = useState(null)

  useEffect(() => {
  fetch(`http://localhost:5000/api/runs/${runId}`)
    .then(res => res.json())
    .then(data => setRunDetails(data))
}, [runId])

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
    <div>
      <h1>Attempt</h1>
      <button onClick={() => navigate('/')}>Home</button>
      {/* {script.map(row => (
        row.event_type === 'Location'
          ? <LocationRow key={row.sort_order} row={row} gameId={runDetails?.game_id} />
          : <BossRow key={row.sort_order} row={row} />
      ))} */}
      {script.map(row => renderScriptRow(row))}
    </div>
  )
}

export default Attempt