import { useNavigate } from 'react-router-dom'

function Home() {
  const navigate = useNavigate()

  return (
    <div>
      <h1>Lockley</h1>
      <h2>Nuzlocke Tracker</h2>
      <button onClick={ () => navigate('/new-run')}> New Game </button> 
      <button onClick={ () => navigate('/load-run')}> Load Game </button>
    </div>
  )
}

export default Home