
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import NewRun from './pages/NewRun'
import LoadRun from './pages/LoadRun'
import Attempt from './pages/Attempt'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/new-run" element={<NewRun />} />
        <Route path="/load-run" element={<LoadRun />} />
        <Route path="/attempt/:runId" element={<Attempt />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
