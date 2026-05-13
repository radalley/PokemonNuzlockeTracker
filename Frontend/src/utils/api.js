import { supabase } from '../lib/supabase'

/**
 * Wrapper around fetch that automatically attaches the Supabase JWT
 * as an Authorization header on every request to the Flask backend.
 */
const API_BASE = import.meta.env.VITE_API_URL || ''

export async function apiFetch(url, options = {}) {
  const { data: { session } } = await supabase.auth.getSession()

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }

  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`
  }

  const response = await fetch(API_BASE + url, { ...options, headers })
  return response
}
