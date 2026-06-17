/** Catches render-time errors so a single bad component can't white-screen the app. */
import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = { children: ReactNode }
type State = { error: Error | null }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Render error:', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="page">
          <div className="card">
            <div className="state">
              <div className="state-title state-error">Something went wrong on this page</div>
              <div className="muted" style={{ maxWidth: '52ch' }}>{this.state.error.message}</div>
              <div className="row gap-2">
                <button className="btn" onClick={() => this.setState({ error: null })}>Try again</button>
                <button className="btn btn-primary" onClick={() => { window.location.href = '/' }}>Go to dashboard</button>
              </div>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
