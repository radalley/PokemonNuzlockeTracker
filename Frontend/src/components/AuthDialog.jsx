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
    loginWithGoogle,
    forgotPassword,
    loading,
  } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [forgotMode, setForgotMode] = useState(false)
  const [forgotSent, setForgotSent] = useState(false)
  const [passwordError, setPasswordError] = useState(false)

  useEffect(() => {
    if (!authDialogOpen) {
      setPassword('')
      setError('')
      setSubmitting(false)
      setForgotMode(false)
      setForgotSent(false)
      setPasswordError(false)
    }
  }, [authDialogOpen])

  if (!authDialogOpen || loading) return null

  const isRegister = authDialogMode === 'register'

  async function handleSubmit(event) {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    setPasswordError(false)
    try {
      if (isRegister) {
        await register({ email, password, displayName })
      } else {
        await login({ email, password })
      }
    } catch (submitError) {
      setError(submitError.message)
      if (!isRegister) setPasswordError(true)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleForgotSubmit(event) {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      await forgotPassword(email)
      setForgotSent(true)
    } catch (forgotError) {
      setError(forgotError.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleGoogle() {
    setSubmitting(true)
    setError('')
    try {
      await loginWithGoogle()
    } catch (oauthError) {
      setError(oauthError.message)
      setSubmitting(false)
    }
  }

  if (forgotMode) {
    return (
      <div className="auth-dialog__backdrop" onClick={closeAuthDialog}>
        <div className="auth-dialog" onClick={event => event.stopPropagation()}>
          <div className="auth-dialog__header">
            <div>
              <h2 className="auth-dialog__title">Reset password</h2>
              <p className="auth-dialog__subtitle">We'll send a reset link to your email.</p>
            </div>
            <button type="button" className="auth-dialog__close" onClick={closeAuthDialog}>Close</button>
          </div>
          {forgotSent ? (
            <div className="auth-dialog__forgot-sent">
              Check your inbox — a reset link has been sent to <strong>{email}</strong>.
            </div>
          ) : (
            <form className="auth-dialog__form" onSubmit={handleForgotSubmit}>
              <label className="auth-dialog__field">
                <span>Email</span>
                <input type="email" value={email} onChange={event => setEmail(event.target.value)} required />
              </label>
              {error && <div className="auth-dialog__error">{error}</div>}
              <button type="submit" className="auth-dialog__submit" disabled={submitting}>
                {submitting ? 'Sending...' : 'Send reset link'}
              </button>
            </form>
          )}
          <div className="auth-dialog__footer">
            <button type="button" className="auth-dialog__switch" onClick={() => { setForgotMode(false); setForgotSent(false); setError('') }}>
              Back to sign in
            </button>
          </div>
        </div>
      </div>
    )
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

        <button
          type="button"
          className="auth-dialog__oauth auth-dialog__oauth--google"
          onClick={handleGoogle}
          disabled={submitting}
        >
          Continue with Google
        </button>

        <div className="auth-dialog__divider"><span>or</span></div>

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
            <span className="auth-dialog__password-row">
              Password
              {!isRegister && (
                <button
                  type="button"
                  className={`auth-dialog__forgot${passwordError ? ' auth-dialog__forgot--visible' : ''}`}
                  onClick={() => { setForgotMode(true); setError(''); setPasswordError(false) }}
                  tabIndex={passwordError ? 0 : -1}
                >
                  Forgot password?
                </button>
              )}
            </span>
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
