import { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'

function AuthDialog() {
  const {
    authDialogOpen,
    authDialogMode,
    closeAuthDialog,
    openAuthDialog,
    login,
    register,
    loading,
  } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!authDialogOpen) {
      setPassword('')
      setError('')
      setSubmitting(false)
    }
  }, [authDialogOpen])

  if (!authDialogOpen || loading) return null

  const isRegister = authDialogMode === 'register'

  async function handleSubmit(event) {
    event.preventDefault()
    setSubmitting(true)
    setError('')

    try {
      if (isRegister) {
        await register({ email, password, displayName })
      } else {
        await login({ email, password })
      }
    } catch (submitError) {
      setError(submitError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-dialog__backdrop" onClick={closeAuthDialog}>
      <div className="auth-dialog" onClick={event => event.stopPropagation()}>
        <div className="auth-dialog__header">
          <div>
            <h2 className="auth-dialog__title">{isRegister ? 'Create account' : 'Sign in'}</h2>
            <p className="auth-dialog__subtitle">Use one account across laptop and PC.</p>
          </div>
          <button type="button" className="auth-dialog__close" onClick={closeAuthDialog}>Close</button>
        </div>

        <form className="auth-dialog__form" onSubmit={handleSubmit}>
          <label className="auth-dialog__field">
            <span>Email</span>
            <input type="email" value={email} onChange={event => setEmail(event.target.value)} required />
          </label>

          {isRegister && (
            <label className="auth-dialog__field">
              <span>Display Name</span>
              <input type="text" value={displayName} onChange={event => setDisplayName(event.target.value)} placeholder="Optional" />
            </label>
          )}

          <label className="auth-dialog__field">
            <span>Password</span>
            <input type="password" value={password} onChange={event => setPassword(event.target.value)} minLength={8} required />
          </label>

          {error && <div className="auth-dialog__error">{error}</div>}

          <button type="submit" className="auth-dialog__submit" disabled={submitting}>
            {submitting ? 'Working...' : isRegister ? 'Create account' : 'Sign in'}
          </button>
        </form>

        <div className="auth-dialog__footer">
          <span>{isRegister ? 'Already have an account?' : 'Need an account?'}</span>
          <button
            type="button"
            className="auth-dialog__switch"
            onClick={() => openAuthDialog(isRegister ? 'login' : 'register')}
          >
            {isRegister ? 'Sign in instead' : 'Create one'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default AuthDialog
