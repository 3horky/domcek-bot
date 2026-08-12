import { cleanup, render, screen } from '@testing-library/react'
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
      details: { publication_execution_mode: 'live' },
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

function mockStatusApi(options?: {
  readinessFailure?: boolean
  operations?: typeof operationsSummary
}) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    const path = String(input)
    if (path.includes('/health/live'))
      return Promise.resolve(
        jsonResponse({ status: 'alive', version: '0.1.0', environment: 'test' }),
      )
    if (path.includes('/health/ready')) {
      if (options?.readinessFailure)
        return Promise.resolve(
          new Response(JSON.stringify({ status: 'not_ready' }), {
            status: 503,
            headers: { 'X-Correlation-ID': 'frontend-test' },
          }),
        )
      return Promise.resolve(
        jsonResponse({ status: 'ready', dependencies: { database: { status: 'healthy' } } }),
      )
    }
    return Promise.resolve(jsonResponse(options?.operations ?? operationsSummary))
  })
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

test('shows ready state when API and database are healthy', async () => {
  mockStatusApi()

  render(<StatusPage />)

  expect(await screen.findByRole('heading', { name: 'Carlo je pripravený' })).toBeInTheDocument()
  expect(screen.getByText('Dostupná')).toBeInTheDocument()
  expect(screen.getByText('Pripojené')).toBeInTheDocument()
  expect(screen.getByText('Plánovač beží')).toBeInTheDocument()
  expect(screen.getByText('3')).toBeInTheDocument()
})

test('shows degraded state when readiness fails', async () => {
  mockStatusApi({ readinessFailure: true })

  render(<StatusPage />)

  expect(
    await screen.findByRole('heading', { name: 'Niečo potrebuje pozornosť' }),
  ).toBeInTheDocument()
  expect(screen.getByText('frontend-test')).not.toBeVisible()
  screen.getByText('Technické údaje pre riešenie problému').click()
  expect(screen.getByText('frontend-test')).toBeInTheDocument()
})

test('warns when more than one worker heartbeat is active', async () => {
  mockStatusApi({
    operations: {
      ...operationsSummary,
      active_instance_counts: { bot: 1, worker: 2 },
    },
  })

  render(<StatusPage />)

  expect(await screen.findByRole('alert')).toHaveTextContent('Beží viac procesov rovnakého typu')
})
