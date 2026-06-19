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
    signOut().catch(() => {
      // Last resort if signOut itself fails: force a hard reload to clear all state
      if (typeof window !== 'undefined') window.location.reload()
    })
  }
  return response
}

export async function logActivity(type: string, data?: Record<string, any>) {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    await apiFetch(`${apiUrl}/api/v1/activity`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ activity_type: type, data: data || {} }),
    })
  } catch (err) {
    console.error('[Activity Tracking] Failed:', err)
  }
}
