import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import SiteHeader from '../components/SiteHeader'

function ResetPassword() {
  const navigate = useNavigate()
  const [ready, setReady] = useState(false)
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  // Supabase fires PASSWORD_RECOVERY when the reset link is opened.
  // The SDK exchanges the token from the URL hash automatically.
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'PASSWORD_RECOVERY') {
        setReady(true)
      }
    })
    return () => subscription.unsubscribe()
  }, [])

  async function handleSubmit(event) {
    event.preventDefault()
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    setError('')
    const { error: updateError } = await supabase.auth.updateUser({ password })
    if (updateError) {
      setError(updateError.message)
      setSubmitting(false)
    } else {
      setDone(true)
      setTimeout(() => navigate('/'), 2500)
    }
  }

  return (
    <div style={{ minHeight: '100svh' }}>
      <SiteHeader showHomeButton />
      <div className="reset-password-page">
        {done ? (
          <>
            <h2 className="reset-password__title">Password updated</h2>
            <p className="reset-password__sub">You're being redirected back home…</p>
          </>
        ) : !ready ? (
          <>
            <h2 className="reset-password__title">Verifying reset link…</h2>
            <p className="reset-password__sub">This should only take a moment.</p>
          </>
        ) : (
          <>
            <h2 className="reset-password__title">Choose a new password</h2>
            <form className="reset-password__form" onSubmit={handleSubmit}>
              <label className="auth-dialog__field">
                <span>New password</span>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  minLength={8}
                  required
                />
              </label>
              <label className="auth-dialog__field">
                <span>Confirm password</span>
                <input
                  type="password"
                  value={confirm}
                  onChange={e => setConfirm(e.target.value)}
                  minLength={8}
                  required
                />
              </label>
              {error && <div className="auth-dialog__error">{error}</div>}
              <button type="submit" className="auth-dialog__submit" disabled={submitting}>
                {submitting ? 'Saving…' : 'Set new password'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}

export default ResetPassword
