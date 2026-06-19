// pages/oauth.tsx — OAuth 2.0 consent / login page
// Reached via: GET /oauth/authorize on the backend (which 302s here)
// On success: redirects browser to redirect_uri?code=...&state=... (MCP client picks it up)
import React, { useState, useEffect } from 'react'
import Head from 'next/head'
import { useRouter } from 'next/router'
import { auth, signInWithGoogle, getCurrentIdToken, onAuthStateChanged, type User } from '@/lib/firebase'

const API_BASE = process.env.NEXT_PUBLIC_API_URL?.replace('localhost:3000', 'localhost:8000') || 'https://baljot07-fusion.hf.space'

type Step = 'loading' | 'sign-in' | 'connecting' | 'done' | 'error'

export default function OAuthPage() {
  const router = useRouter()
  const ready = router.isReady
  const { client_id, redirect_uri, state, code_challenge } = router.query as Record<string, string>

  const [step, setStep] = useState<Step>('loading')
  const [user, setUser] = useState<User | null>(null)
  const [error, setError] = useState('')
  const [didRun, setDidRun] = useState(false)

  // Wait for Firebase to initialize
  useEffect(() => {
    return onAuthStateChanged(auth, (u) => {
      setUser(u)
      if (step === 'loading') setStep(u ? 'connecting' : 'sign-in')
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Auto-complete flow when user + params are ready
  useEffect(() => {
    if (!didRun && step === 'connecting' && user && ready && client_id && redirect_uri) {
      setDidRun(true)
      completeFlow(user)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, user, ready, client_id])

  const completeFlow = async (currentUser: User) => {
    setStep('connecting')
    try {
      const idToken = await currentUser.getIdToken()
      const res = await fetch(`${API_BASE}/oauth/callback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          firebase_token: idToken,
          client_id: client_id || '',
          redirect_uri: redirect_uri || '',
          state: state || '',
          code_challenge: code_challenge || '',
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()

      const url = new URL(data.redirect_uri)
      url.searchParams.set('code', data.code)
      if (data.state) url.searchParams.set('state', data.state)

      setStep('done')
      window.location.href = url.toString()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Connection failed')
      setStep('error')
    }
  }

  const handleGoogleSignIn = async () => {
    setStep('connecting')
    try {
      const result = await signInWithGoogle()
      await completeFlow(result.user)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Sign in failed'
      setError(msg === 'POPUP_BLOCKED' ? 'Pop-up blocked — allow pop-ups for this site and try again.' : msg)
      setStep('error')
    }
  }

  return (
    <>
      <Head>
        <title>Connect to FUSION VC — Authorization</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <div style={{ minHeight: '100vh', background: '#0a0a0f', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif' }}>
        <div style={{ width: '100%', maxWidth: 380, background: '#111118', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 20, padding: 32, boxShadow: '0 24px 64px rgba(0,0,0,0.6)' }}>

          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
            <div style={{ width: 44, height: 44, borderRadius: 12, background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, fontWeight: 700, color: '#fff' }}>F</div>
            <div>
              <p style={{ margin: 0, color: '#fff', fontWeight: 600, fontSize: 14 }}>FUSION VC Committee</p>
              <p style={{ margin: 0, color: '#6b7280', fontSize: 12 }}>AI-powered investment analysis</p>
            </div>
          </div>

          {/* Content by step */}
          {step === 'loading' && (
            <div style={{ textAlign: 'center', padding: '16px 0' }}>
              <div style={{ width: 28, height: 28, border: '2px solid rgba(255,255,255,0.15)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 0.7s linear infinite', margin: '0 auto 12px' }} />
              <p style={{ color: '#9ca3af', fontSize: 13, margin: 0 }}>Initializing…</p>
            </div>
          )}

          {step === 'sign-in' && (
            <>
              <p style={{ color: '#d1d5db', fontSize: 14, margin: '0 0 6px' }}>An AI assistant wants to connect.</p>
              <p style={{ color: '#6b7280', fontSize: 12, margin: '0 0 24px' }}>Sign in to link your private deal history and analysis. Your data is isolated to your account.</p>
              <button onClick={handleGoogleSignIn} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, background: '#fff', color: '#111', fontSize: 14, fontWeight: 600, padding: '11px 16px', borderRadius: 12, border: 'none', cursor: 'pointer' }}>
                <svg width="18" height="18" viewBox="0 0 18 18">
                  <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z"/>
                  <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z"/>
                  <path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z"/>
                  <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z"/>
                </svg>
                Continue with Google
              </button>
              <p style={{ color: '#374151', fontSize: 11, textAlign: 'center', marginTop: 16 }}>
                Private to your account · No deal data is shared
              </p>
            </>
          )}

          {step === 'connecting' && (
            <div style={{ textAlign: 'center', padding: '16px 0' }}>
              <div style={{ width: 28, height: 28, border: '2px solid rgba(255,255,255,0.15)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 0.7s linear infinite', margin: '0 auto 12px' }} />
              <p style={{ color: '#d1d5db', fontSize: 13, margin: 0 }}>Connecting to FUSION…</p>
            </div>
          )}

          {step === 'done' && (
            <div style={{ textAlign: 'center', padding: '16px 0' }}>
              <div style={{ width: 48, height: 48, borderRadius: '50%', background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 12px' }}>
                <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="#10b981"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
              </div>
              <p style={{ color: '#fff', fontWeight: 600, fontSize: 15, margin: '0 0 4px' }}>Connected!</p>
              <p style={{ color: '#6b7280', fontSize: 12, margin: 0 }}>You can close this tab and return to your AI assistant.</p>
            </div>
          )}

          {step === 'error' && (
            <div style={{ textAlign: 'center', padding: '8px 0' }}>
              <p style={{ color: '#f87171', fontSize: 13, margin: '0 0 12px' }}>{error}</p>
              <button onClick={() => { setStep('sign-in'); setError(''); setDidRun(false) }} style={{ color: '#9ca3af', fontSize: 12, background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}>
                Try again
              </button>
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        * { box-sizing: border-box; }
      `}</style>
    </>
  )
}
