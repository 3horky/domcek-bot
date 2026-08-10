import { render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { StatusPage } from './StatusPage'

const operationsSummary = {
  observed_at: '2026-08-10T18:00:00+00:00',
  next_publication: {
    slot_key: '1535774834955391047:2026-08-10T20:00:00+02:00',
    scheduled_for: '2026-08-10T18:00:00+00:00',
  },
  processes: [
    {
      process_name: 'bot',
      instance_id: '11111111-1111-4111-8111-111111111111',
      state: 'connected',
      healthy: true,
      started_at: '2026-08-10T17:00:00+00:00',
      last_seen_at: '2026-08-10T17:59:50+00:00',
      details: { latency_ms: 22 },
    },
    {
      process_name: 'worker',
      instance_id: '22222222-2222-4222-8222-222222222222',
      state: 'running',
      healthy: true,
      started_at: '2026-08-10T17:00:00+00:00',
      last_seen_at: '2026-08-10T17:59:55+00:00',
      details: { publication_execution_mode: 'shadow' },
    },
  ],
  active_instance_counts: { bot: 1, worker: 1 },
  calendars: [],
  publication_metrics: {
    sample_size: 4,
    successful: 3,
    failed: 1,
    in_progress: 0,
    skipped: 0,
  },
  recent_tasks: [],
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  vi.restoreAllMocks()
})

test('shows ready state when API and database are healthy', async () => {
  vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(jsonResponse({ status: 'alive', version: '0.1.0', environment: 'test' }))
    .mockResolvedValueOnce(
      jsonResponse({ status: 'ready', dependencies: { database: { status: 'healthy' } } }),
    )
    .mockResolvedValueOnce(jsonResponse(operationsSummary))

  render(<StatusPage />)

  expect(await screen.findByRole('heading', { name: 'Pripravené' })).toBeInTheDocument()
  expect(screen.getByText('healthy')).toBeInTheDocument()
  expect(screen.getByText('Pripojený')).toBeInTheDocument()
  expect(screen.getByText(/1 aktívna inštancia · režim/)).toHaveTextContent('shadow')
  expect(screen.getByText('3')).toBeInTheDocument()
})

test('shows degraded state when readiness fails', async () => {
  vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(jsonResponse({ status: 'alive', version: '0.1.0', environment: 'test' }))
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'not_ready' }), {
        status: 503,
        headers: { 'X-Correlation-ID': 'frontend-test' },
      }),
    )
    .mockResolvedValueOnce(jsonResponse(operationsSummary))

  render(<StatusPage />)

  expect(await screen.findByRole('heading', { name: 'Čiastočne dostupné' })).toBeInTheDocument()
  expect(screen.getByText('frontend-test')).toBeInTheDocument()
})

test('warns when more than one worker heartbeat is active', async () => {
  vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(jsonResponse({ status: 'alive', version: '0.1.0', environment: 'test' }))
    .mockResolvedValueOnce(
      jsonResponse({ status: 'ready', dependencies: { database: { status: 'healthy' } } }),
    )
    .mockResolvedValueOnce(
      jsonResponse({
        ...operationsSummary,
        active_instance_counts: { bot: 1, worker: 2 },
      }),
    )

  render(<StatusPage />)

  expect(await screen.findByRole('alert')).toHaveTextContent(
    'viac aktívnych inštancií: bot 1, worker 2',
  )
})
