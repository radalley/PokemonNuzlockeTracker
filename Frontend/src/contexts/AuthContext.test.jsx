import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AuthDialog from '../components/AuthDialog'
import { supabase } from '../lib/supabase'
import { AuthProvider, useAuth } from './AuthContext'

vi.mock('../lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
      onAuthStateChange: vi.fn(),
      signInWithPassword: vi.fn(),
      signInWithOAuth: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      resetPasswordForEmail: vi.fn(),
    },
  },
}))

vi.mock('../utils/api', () => ({
  apiFetch: vi.fn(),
}))

function AuthHarness() {
  const { loading, openAuthDialog } = useAuth()

  return (
    <>
      <span data-testid="loading">{String(loading)}</span>
      <button type="button" data-testid="open-auth" onClick={() => openAuthDialog('login')}>
        Open auth
      </button>
      <AuthDialog />
    </>
  )
}

describe('AuthProvider initialization', () => {
  let container
  let root
  let unsubscribe

  beforeEach(() => {
    globalThis.IS_REACT_ACT_ENVIRONMENT = true
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
    unsubscribe = vi.fn()
    supabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe } },
    })
  })

  afterEach(async () => {
    await act(async () => root.unmount())
    container.remove()
    vi.clearAllMocks()
  })

  it('opens the sign-in dialog while session restoration is still pending', async () => {
    supabase.auth.getSession.mockReturnValue(new Promise(() => {}))

    await act(async () => root.render(<AuthProvider><AuthHarness /></AuthProvider>))
    await act(async () => container.querySelector('[data-testid="open-auth"]').click())

    expect(container.querySelector('.auth-dialog__title')?.textContent).toBe('Sign in')
    expect(container.querySelector('[data-testid="loading"]').textContent).toBe('true')
  })

  it('finishes initialization when restoring a session fails', async () => {
    const error = new Error('auth service unavailable')
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    supabase.auth.getSession.mockRejectedValue(error)

    await act(async () => {
      root.render(<AuthProvider><AuthHarness /></AuthProvider>)
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(container.querySelector('[data-testid="loading"]').textContent).toBe('false')
    expect(consoleError).toHaveBeenCalledWith('Failed to restore auth session:', error)
  })
})
