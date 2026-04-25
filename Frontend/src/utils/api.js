import { supabase } from '../lib/supabase'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/$/, '')

function resolveApiUrl(url) {
  if (!API_BASE_URL) return url
  if (/^https?:\/\//i.test(url)) return url
  return `${API_BASE_URL}${url.startsWith('/') ? url : `/${url}`}`
}

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

  const response = await fetch(resolveApiUrl(url), { ...options, headers })
  return response
}
