// lib/apiFetch.ts — drop-in fetch wrapper that injects Firebase auth token
import { getCurrentIdToken } from './firebase'

/**
 * Same API as window.fetch — just auto-adds Authorization: Bearer <firebase_token>.
 * Use this everywhere instead of bare fetch() for authenticated requests.
 */
export async function apiFetch(url: string, init?: RequestInit): Promise<Response> {
  const token = await getCurrentIdToken()
  const headers = new Headers(init?.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  // Keep Content-Type if caller set it (e.g. application/json), don't override FormData
  return fetch(url, { ...init, headers })
}
