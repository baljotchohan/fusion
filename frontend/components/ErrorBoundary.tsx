// components/ErrorBoundary.tsx — catches render errors so one bad component
// doesn't blank the entire dashboard.
import React from 'react'

interface Props { children: React.ReactNode }
interface State { error: Error | null; resetKey: number }

export default class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null, resetKey: 0 }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex flex-col items-center justify-center h-full p-8 text-center gap-4">
          <p className="text-danger font-semibold text-[14px]">Something went wrong</p>
          <p className="text-text-muted text-[12px] max-w-xs">{this.state.error.message}</p>
          <button
            onClick={() => this.setState(s => ({ error: null, resetKey: s.resetKey + 1 }))}
            className="px-4 py-2 rounded-lg border border-border text-[12px] text-text-secondary hover:bg-bg-muted transition cursor-pointer"
          >
            Try again
          </button>
        </div>
      )
    }
    return <React.Fragment key={this.state.resetKey}>{this.props.children}</React.Fragment>
  }
}
