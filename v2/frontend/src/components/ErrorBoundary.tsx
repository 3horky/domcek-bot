import { Component, type ErrorInfo, type ReactNode } from 'react'

import { Button } from './ui/button'

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
          <div>
            <p className="eyebrow">Carlo</p>
            <h1>Rozhranie sa nepodarilo zobraziť</h1>
            <p>Obnovte stránku. Ak problém pretrváva, oznámte ho administrátorovi.</p>
            <Button type="button" onClick={() => window.location.reload()}>
              Obnoviť stránku
            </Button>
          </div>
        </main>
      )
    }
    return this.props.children
  }
}
