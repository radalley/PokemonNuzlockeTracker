import { useNavigate } from 'react-router-dom'

function Home() {
  const navigate = useNavigate()

  return (
    <div>
      <h1>Lockley</h1>
      <h2>Nuzlocke Tracker</h2>
      <button onClick={ () => navigate('/new-run')}> New Game </button> 
      <button onClick={ () => navigate('/load-run')}> Load Game </button>

      <p style={{ fontSize: '0.8em', color: '#666', marginTop: '20px', textAlign: 'center' }}>
        Pokémon and its trademarks are ©1995-2023 Nintendo/Creatures Inc./GAME FREAK inc. TM, ® and © 1995-2023 Nintendo.
      </p>
    </div>
  )
}

export default Home