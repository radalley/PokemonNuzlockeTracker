import { supabase } from '../lib/supabase'

/**
 * Wrapper around fetch that automatically attaches the Supabase JWT
 * as an Authorization header on every request to the Flask backend.
 */
export async function apiFetch(url, options = {}) {
  const { data: { session } } = await supabase.auth.getSession()

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }

  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`
  }

  const response = await fetch(url, { ...options, headers })
  return response
}
