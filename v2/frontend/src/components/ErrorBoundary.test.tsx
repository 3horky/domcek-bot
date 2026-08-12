import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ErrorBoundary } from './ErrorBoundary'

function BrokenView(): never {
  throw new Error('test failure')
}

describe('ErrorBoundary', () => {
  afterEach(() => vi.restoreAllMocks())

  it('nahradí technický pád zrozumiteľnou recovery obrazovkou', () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined)

    render(
      <ErrorBoundary>
        <BrokenView />
      </ErrorBoundary>,
    )

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Rozhranie sa nepodarilo zobraziť' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Obnoviť stránku' })).toBeEnabled()
    expect(screen.queryByText('test failure')).not.toBeInTheDocument()
  })
})
