
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import NewRun from './pages/NewRun'
import LoadRun from './pages/LoadRun'
import Guides from './pages/Guides'
import Attempt from './pages/Attempt'
import Box from './pages/Box'
import Graveyard from './pages/Graveyard'
import ResetPassword from './pages/ResetPassword'
import ErrorBoundary from './components/ErrorBoundary'
import AuthDialog from './components/AuthDialog'
import { AuthProvider } from './contexts/AuthContext'

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <AuthDialog />
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/new-run" element={<NewRun />} />
            <Route path="/load-run" element={<LoadRun />} />
            <Route path="/guides" element={<Guides />} />
            <Route path="/attempt/:runId/:attemptId" element={<Attempt />} />
            <Route path="/box/:runId/:attemptId" element={<Box />} />
            <Route path="/graveyard/:runId/:attemptId" element={<Graveyard />} />
            <Route path="/reset-password" element={<ResetPassword />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  )
}

export default App
