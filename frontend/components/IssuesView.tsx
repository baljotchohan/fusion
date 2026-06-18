// components/IssuesView.tsx — report errors & feedback
import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertCircle, CheckCircle, Send, RefreshCw } from 'lucide-react'
import { API_BASE } from '@/lib/agents'
import { apiFetch, logActivity } from '@/lib/apiFetch'

export default function IssuesView() {
  const [errorMessage, setErrorMessage] = useState('')
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle')
  const [apiError, setApiError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!errorMessage.trim() || status === 'submitting') return

    setStatus('submitting')
    setApiError(null)

    try {
      logActivity('issue_submit_attempt', { length: errorMessage.length })
      const response = await apiFetch(`${API_BASE}/api/v1/issues`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error_message: errorMessage }),
      })

      if (!response.ok) {
        throw new Error('Failed to submit the issue. Please check your backend connection.')
      }

      setStatus('success')
      setErrorMessage('')
      logActivity('issue_submit_success')
    } catch (err: any) {
      console.error('Submit issue failed:', err)
      setStatus('error')
      setApiError(err.message || 'An unexpected error occurred. Please try again.')
      logActivity('issue_submit_failed', { error: err.message })
    }
  }

  const sectionCls = 'rounded-2xl bg-bg-card border border-border shadow-sm p-6 max-w-xl mx-auto'
  const labelCls = 'text-[10px] font-semibold uppercase tracking-wider text-text-muted'

  return (
    <div className="h-full overflow-y-auto px-6 py-8 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-[22px] font-bold text-text-primary tracking-tight">Report an Issue</h1>
        <p className="text-[13px] text-text-secondary mt-1">
          Encountered a bug, a layout error, or a failed audit? Tell us what went wrong.
        </p>
      </div>

      <motion.section 
        layout
        className={sectionCls}
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
      >
        <div className="flex items-center gap-2 mb-4">
          <AlertCircle className="w-4 h-4 text-accent" />
          <p className={labelCls}>Issue Details</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="issue-textarea" className="sr-only">Describe the error</label>
            <textarea
              id="issue-textarea"
              value={errorMessage}
              onChange={(e) => setErrorMessage(e.target.value)}
              placeholder="Describe the error, what page/tab you were on, and steps to reproduce..."
              disabled={status === 'submitting'}
              rows={6}
              className="w-full bg-bg-subtle border border-border rounded-xl px-4 py-3 text-[13px] leading-relaxed focus:outline-none focus:border-accent/45 focus:shadow-[0_0_12px_rgba(91,191,82,0.15)] text-text-primary placeholder:text-text-muted transition-all duration-300 resize-none"
            />
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[11px] text-text-muted">
              {errorMessage.trim().length} characters
            </span>

            <button
              type="submit"
              disabled={!errorMessage.trim() || status === 'submitting'}
              className={`h-9 px-4 rounded-lg text-[12px] font-semibold flex items-center gap-2 transition-all duration-150 active:scale-95 cursor-pointer ${
                errorMessage.trim() && status !== 'submitting'
                  ? 'bg-accent text-white hover:bg-accent/95 shadow-sm'
                  : 'bg-bg-muted text-text-muted cursor-not-allowed'
              }`}
            >
              {status === 'submitting' ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  Submit Issue
                </>
              )}
            </button>
          </div>
        </form>

        <AnimatePresence mode="wait">
          {status === 'success' && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mt-4 rounded-xl bg-success-soft border border-success/20 px-4 py-3 flex items-start gap-2.5 text-left"
            >
              <CheckCircle className="w-4 h-4 text-success mt-0.5 shrink-0" />
              <div>
                <h4 className="text-[12px] font-semibold text-success">Issue reported successfully</h4>
                <p className="text-[11px] text-text-secondary mt-0.5">
                  Thank you for your feedback! The error message has been saved to the database.
                </p>
              </div>
            </motion.div>
          )}

          {status === 'error' && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mt-4 rounded-xl bg-danger-soft border border-danger/25 px-4 py-3 flex items-start gap-2.5 text-left"
            >
              <AlertCircle className="w-4 h-4 text-danger mt-0.5 shrink-0" />
              <div>
                <h4 className="text-[12px] font-semibold text-danger">Submission failed</h4>
                <p className="text-[11px] text-danger mt-0.5">{apiError}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.section>
    </div>
  )
}
