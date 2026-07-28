
import { Suspense, lazy } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import ErrorBoundary from './components/ErrorBoundary'
import AuthDialog from './components/AuthDialog'
import { AuthProvider } from './contexts/AuthContext'

// Route-level code splitting: each page's JS is only fetched when the user
// actually navigates to it, instead of all pages shipping in the initial bundle.
const Home = lazy(() => import('./pages/Home'))
const NewRun = lazy(() => import('./pages/NewRun'))
const LoadRun = lazy(() => import('./pages/LoadRun'))
const Guides = lazy(() => import('./pages/Guides'))
const Attempt = lazy(() => import('./pages/Attempt'))
const Box = lazy(() => import('./pages/Box'))
const Graveyard = lazy(() => import('./pages/Graveyard'))
const ResetPassword = lazy(() => import('./pages/ResetPassword'))
const AdminReports = lazy(() => import('./pages/AdminReports'))

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <AuthDialog />
          <Suspense fallback={null}>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/new-run" element={<NewRun />} />
              <Route path="/load-run" element={<LoadRun />} />
              <Route path="/guides" element={<Guides />} />
              <Route path="/attempt/:runId/:attemptId" element={<Attempt />} />
              <Route path="/box/:runId/:attemptId" element={<Box />} />
              <Route path="/graveyard/:runId/:attemptId" element={<Graveyard />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/admin/reports" element={<AdminReports />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  )
}

export default App
