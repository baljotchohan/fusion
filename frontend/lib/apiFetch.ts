// lib/apiFetch.ts — drop-in fetch wrapper that injects Firebase auth token
import { getCurrentIdToken, signOut } from './firebase'

/**
 * Same API as window.fetch — just auto-adds Authorization: Bearer <firebase_token>.
 * Use this everywhere instead of bare fetch() for authenticated requests.
 * On 401 (expired/revoked token) automatically signs the user out so they
 * land back on the login screen rather than being silently stuck.
 */
export async function apiFetch(url: string, init?: RequestInit): Promise<Response> {
  const token = await getCurrentIdToken()
  const headers = new Headers(init?.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  // Keep Content-Type if caller set it (e.g. application/json), don't override FormData
  const response = await fetch(url, { ...init, headers })
  if (response.status === 401) {
    // Token expired or revoked — sign out so onAuthStateChanged routes to login
    signOut().catch(() => {})
  }
  return response
}
