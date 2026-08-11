import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { EmptyState, LoadErrorState, LoadingState } from './AsyncState'

describe('AsyncState', () => {
  it('oznamuje načítanie a prázdny výsledok ako stav', () => {
    const { rerender } = render(<LoadingState label="Načítavam pravidlá…" />)
    expect(screen.getByRole('status')).toHaveTextContent('Načítavam pravidlá…')

    rerender(<EmptyState title="Zatiaľ nič" detail="Vytvorte prvú položku." />)
    expect(screen.getByRole('status')).toHaveTextContent('Zatiaľ nič')
  })

  it('oznámi chybu a ponúkne funkčnú obnovu', () => {
    const retry = vi.fn()
    render(<LoadErrorState detail="Spojenie bolo prerušené." onRetry={retry} />)

    expect(screen.getByRole('alert')).toHaveTextContent('Spojenie bolo prerušené.')
    fireEvent.click(screen.getByRole('button', { name: 'Skúsiť znova' }))
    expect(retry).toHaveBeenCalledOnce()
  })
})
