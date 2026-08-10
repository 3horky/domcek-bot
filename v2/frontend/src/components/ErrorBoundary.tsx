import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  failed: boolean
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Unexpected UI error', error, info)
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="fatal-error" role="alert">
          <p className="eyebrow">Carlo</p>
          <h1>Rozhranie sa nepodarilo zobraziť</h1>
          <p>Obnov stránku. Ak problém pretrváva, oznám ho administrátorovi.</p>
          <button type="button" onClick={() => window.location.reload()}>
            Obnoviť stránku
          </button>
        </main>
      )
    }
    return this.props.children
  }
}
