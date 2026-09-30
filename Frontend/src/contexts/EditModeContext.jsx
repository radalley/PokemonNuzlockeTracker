import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { useAuth } from './AuthContext'

const STORAGE_KEY = 'lockley.adminEditMode'

function readStored() {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

const EditModeContext = createContext({ canEdit: false, editMode: false, toggleEditMode: () => {} })

/**
 * The one admin edit switch, toggled from the header: trainer reorder,
 * seen-move editing and the split item editor all follow it. It persists
 * across page loads, and only ever reads as on for an admin account.
 */
export function EditModeProvider({ children }) {
  const { user } = useAuth()
  const canEdit = user?.account_type === 'admin'
  const [stored, setStored] = useState(readStored)

  const toggleEditMode = useCallback(() => {
    setStored(prev => {
      const next = !prev
      try {
        window.localStorage.setItem(STORAGE_KEY, next ? '1' : '0')
      } catch {
        // Storage blocked: the toggle still works for this page load.
      }
      return next
    })
  }, [])

  const value = useMemo(
    () => ({ canEdit, editMode: canEdit && stored, toggleEditMode }),
    [canEdit, stored, toggleEditMode],
  )
  return <EditModeContext.Provider value={value}>{children}</EditModeContext.Provider>
}

// Outside a provider (isolated component tests) edit mode reads as off.
export function useEditMode() {
  return useContext(EditModeContext)
}
