// lib/firebase.ts — Firebase client SDK (auth only, no Firestore needed)
import { initializeApp, getApps } from 'firebase/app'
import {
  getAuth,
  getRedirectResult,
  GoogleAuthProvider,
  signInWithPopup,
  signInAnonymously,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  setPersistence,
  browserLocalPersistence,
  type User,
} from 'firebase/auth'

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
  databaseURL: process.env.NEXT_PUBLIC_FIREBASE_DATABASE_URL,
}

// Prevent duplicate initialization in Next.js hot-reload
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0]
export const auth = getAuth(app)
// Pin persistence so both Google and guest sessions survive refresh/browser-close.
// Must be called before any sign-in; ignored if already set (idempotent).
setPersistence(auth, browserLocalPersistence).catch(() => {})

// Silently handle any pending redirect from a previous broken attempt.
// signInWithRedirect is broken in Chrome M115+/Firefox 109+/Safari 16.1+ due to
// third-party storage blocking — we no longer use it, but clean up if mid-flow.
getRedirectResult(auth).catch(() => {})

const googleProvider = new GoogleAuthProvider()
googleProvider.setCustomParameters({ prompt: 'select_account' })

export const signInWithGoogle = async () => {
  try {
    return await signInWithPopup(auth, googleProvider)
  } catch (error: any) {
    if (error?.code === 'auth/popup-blocked' || error?.code === 'auth/cancelled-popup-request') {
      // signInWithRedirect is broken in modern browsers — surface a clear message instead.
      throw new Error('POPUP_BLOCKED')
    }
    throw error
  }
}
export const signInAsGuest = () => signInAnonymously(auth)
export const signOut = () => firebaseSignOut(auth)

/** Returns the current user's fresh ID token (auto-refreshed by Firebase). */
export const getCurrentIdToken = async (): Promise<string | null> => {
  const user = auth.currentUser
  if (!user) return null
  try {
    return await user.getIdToken()
  } catch {
    return null
  }
}

export type { User }
export { onAuthStateChanged }
