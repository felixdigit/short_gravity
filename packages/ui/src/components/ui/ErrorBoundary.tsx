'use client'

import { Component, type ReactNode } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
  name?: string
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error) {
    console.error(`[ErrorBoundary${this.props.name ? `: ${this.props.name}` : ''}]`, error.message)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback

      return (
        <div className="border border-white/[0.06] bg-white/[0.02] p-3 font-mono">
          <div className="text-[9px] text-white/30 tracking-wider mb-1">
            {this.props.name ? `${this.props.name.toUpperCase()} ` : ''}ERROR
          </div>
          <div className="text-[10px] text-white/40 mb-2">
            {this.state.error?.message || 'Something went wrong'}
          </div>
          <button
            onClick={this.handleRetry}
            className="text-[9px] text-white/50 tracking-wider border border-white/10 px-2 py-0.5 hover:border-white/20 transition-colors"
          >
            RETRY
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
