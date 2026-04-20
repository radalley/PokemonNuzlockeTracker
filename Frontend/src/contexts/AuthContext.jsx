import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

const AuthContext = createContext(null)

async function parseJson(response) {
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.error || 'Request failed')
  }
  return data
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [authDialogOpen, setAuthDialogOpen] = useState(false)
  const [authDialogMode, setAuthDialogMode] = useState('login')

  const refreshUser = useCallback(async () => {
    try {
      const response = await fetch('/api/auth/me')
      const data = await response.json()
      setUser(data.user || null)
    } catch (error) {
      console.error('Failed to fetch current user:', error)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshUser()
  }, [refreshUser])

  const openAuthDialog = useCallback((mode = 'login') => {
    setAuthDialogMode(mode)
    setAuthDialogOpen(true)
  }, [])

  const closeAuthDialog = useCallback(() => {
    setAuthDialogOpen(false)
  }, [])

  const login = useCallback(async ({ email, password }) => {
    const data = await parseJson(await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    }))
    setUser(data.user)
    setAuthDialogOpen(false)
    return data.user
  }, [])

  const register = useCallback(async ({ email, password, displayName }) => {
    const data = await parseJson(await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email,
        password,
        display_name: displayName,
      }),
    }))
    setUser(data.user)
    setAuthDialogOpen(false)
    return data.user
  }, [])

  const logout = useCallback(async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' })
    } catch (error) {
      console.error('Failed to log out:', error)
    }
    setUser(null)
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
    logout,
    refreshUser,
  }), [user, loading, authDialogOpen, authDialogMode, openAuthDialog, closeAuthDialog, login, register, logout, refreshUser])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return value
}
