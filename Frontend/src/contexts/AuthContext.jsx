import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { supabase } from '../lib/supabase'
import { apiFetch } from '../utils/api'

const AuthContext = createContext(null)

function userFromSupabaseSession(session) {
  if (!session?.user) return null
  const fallbackUser = session.user
  return {
    user_id: null,
    email: fallbackUser.email || '',
    display_name: fallbackUser.user_metadata?.display_name || fallbackUser.user_metadata?.full_name || fallbackUser.email || 'Signed in',
    account_type: null,
    backend_unavailable: true,
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [authDialogOpen, setAuthDialogOpen] = useState(false)
  const [authDialogMode, setAuthDialogMode] = useState('login')

  // Fetch the local backend user record using the current Supabase session
  const refreshUser = useCallback(async () => {
    try {
      const response = await apiFetch('/api/auth/me')
      if (!response.ok) {
        throw new Error(`Backend auth check failed with ${response.status}`)
      }
      const data = await response.json()
      if (data.user) {
        setUser(data.user)
      } else {
        const { data: { session } } = await supabase.auth.getSession()
        setUser(userFromSupabaseSession(session))
      }
    } catch (error) {
      console.error('Failed to fetch current user:', error)
      const { data: { session } } = await supabase.auth.getSession()
      setUser(current => current || userFromSupabaseSession(session))
    } finally {
      setLoading(false)
    }
  }, [])

  // Listen for Supabase auth state changes (login, logout, token refresh, OAuth callback)
  useEffect(() => {
    let active = true

    async function restoreSession() {
      try {
        const { data: { session }, error } = await supabase.auth.getSession()
        if (error) throw error
        if (!active) return

        if (session) {
          await refreshUser()
        } else {
          setUser(null)
          setLoading(false)
        }
      } catch (error) {
        console.error('Failed to restore auth session:', error)
        if (active) {
          setUser(null)
          setLoading(false)
        }
      }
    }

    restoreSession()

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        refreshUser()
      } else {
        setUser(null)
        setLoading(false)
      }
    })

    return () => {
      active = false
      subscription.unsubscribe()
    }
  }, [refreshUser])

  const openAuthDialog = useCallback((mode = 'login') => {
    setAuthDialogMode(mode)
    setAuthDialogOpen(true)
  }, [])

  const closeAuthDialog = useCallback(() => {
    setAuthDialogOpen(false)
  }, [])

  const login = useCallback(async ({ email, password }) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw new Error(error.message)
    setAuthDialogOpen(false)
  }, [])

  const register = useCallback(async ({ email, password, displayName }) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { display_name: displayName } },
    })
    if (error) throw new Error(error.message)
    setAuthDialogOpen(false)
  }, [])

  const loginWithGoogle = useCallback(async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    })
    if (error) throw new Error(error.message)
  }, [])

  const logout = useCallback(async () => {
    await supabase.auth.signOut()
    setUser(null)
  }, [])

  const forgotPassword = useCallback(async (email) => {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    })
    if (error) throw new Error(error.message)
  }, [])

  const value = useMemo(() => ({
    user,
    loading,
    authDialogOpen,
    authDialogMode,
    openAuthDialog,
    closeAuthDialog,
    login,
    register,
    loginWithGoogle,
    logout,
    forgotPassword,
    refreshUser,
  }), [user, loading, authDialogOpen, authDialogMode, openAuthDialog, closeAuthDialog, login, register, loginWithGoogle, logout, forgotPassword, refreshUser])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return value
}
