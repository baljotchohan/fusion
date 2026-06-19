import "@/styles/globals.css";
import type { AppProps } from "next/app";
import React, { useState, useEffect, createContext, useContext } from "react";
import ErrorBoundary from "@/components/ErrorBoundary";
import { auth, onAuthStateChanged, type User } from "@/lib/firebase";

interface AuthState { user: User | null; loading: boolean }
export const AuthContext = createContext<AuthState>({ user: null, loading: true })
export function useAuth() { return useContext(AuthContext) }

export default function App({ Component, pageProps }: AppProps) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => {
      setUser(u)
      setLoading(false)
    })
    // Safety: if Firebase never calls back (offline, misconfigured), stop spinning after 8s
    const timer = setTimeout(() => setLoading(false), 8000)
    return () => { unsub(); clearTimeout(timer) }
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading }}>
      <ErrorBoundary>
        <Component {...pageProps} />
      </ErrorBoundary>
    </AuthContext.Provider>
  )
}
