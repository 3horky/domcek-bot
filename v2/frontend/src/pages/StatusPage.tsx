import { useEffect, useState } from 'react'

import {
  ApiError,
  getLiveness,
  getOperationsSummary,
  getReadiness,
  type LivenessResponse,
  type OperationsSummary,
  type ReadinessResponse,
} from '../api/client'

type LoadState = 'loading' | 'ready' | 'degraded' | 'offline'

interface SystemState {
  state: LoadState
  live: LivenessResponse | null
  ready: ReadinessResponse | null
  operations: OperationsSummary | null
  correlationId: string | null
}

const initialState: SystemState = {
  state: 'loading',
  live: null,
  ready: null,
  operations: null,
  correlationId: null,
}

async function loadSystemState(signal?: AbortSignal): Promise<SystemState> {
  const liveResult = await Promise.allSettled([
    getLiveness(signal),
    getReadiness(signal),
    getOperationsSummary(signal),
  ])
  const live = liveResult[0]
  const ready = liveResult[1]
  const operations = liveResult[2]

  if (live.status === 'rejected') {
    const correlationId = live.reason instanceof ApiError ? live.reason.correlationId : null
    return { state: 'offline', live: null, ready: null, operations: null, correlationId }
  }
  if (ready.status === 'rejected' || operations.status === 'rejected') {
    const reason =
      ready.status === 'rejected'
        ? ready.reason
        : operations.status === 'rejected'
          ? operations.reason
          : null
    const correlationId = reason instanceof ApiError ? reason.correlationId : null
    return {
      state: 'degraded',
      live: live.value,
      ready: ready.status === 'fulfilled' ? ready.value : null,
      operations: operations.status === 'fulfilled' ? operations.value : null,
      correlationId,
    }
  }
  return {
    state: 'ready',
    live: live.value,
    ready: ready.value,
    operations: operations.value,
    correlationId: null,
  }
}

function dateTime(value: string | null | undefined): string {
  if (!value) return 'zatiaľ bez údaja'
  return new Intl.DateTimeFormat('sk-SK', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value))
}

function instanceCountLabel(count: number): string {
  if (count === 1) return '1 aktívna inštancia'
  if (count >= 2 && count <= 4) return `${count} aktívne inštancie`
  return `${count} aktívnych inštancií`
}

export function StatusPage() {
  const [system, setSystem] = useState<SystemState>(initialState)

  async function refresh() {
    setSystem((current) => ({ ...current, state: 'loading' }))
    setSystem(await loadSystemState())
  }

  useEffect(() => {
    const controller = new AbortController()
    void loadSystemState(controller.signal).then((nextState) => {
      if (!controller.signal.aborted) setSystem(nextState)
    })
    return () => controller.abort()
  }, [])

  const statusLabel = {
    loading: 'Kontrolujem',
    ready: 'Pripravené',
    degraded: 'Čiastočne dostupné',
    offline: 'Nedostupné',
  }[system.state]
  const bot = system.operations?.processes.find((process) => process.process_name === 'bot')
  const worker = system.operations?.processes.find((process) => process.process_name === 'worker')
  const botInstances = system.operations?.active_instance_counts?.bot ?? 0
  const workerInstances = system.operations?.active_instance_counts?.worker ?? 0
  const duplicateProcess = botInstances > 1 || workerInstances > 1
  const metrics = system.operations?.publication_metrics

  return (
    <section className="page-stack" aria-labelledby="page-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Prevádzková diagnostika</p>
          <h1 id="page-title">Stav systému</h1>
          <p>API, databáza, Discord, plánovač, kalendáre a posledné úlohy.</p>
        </div>
        <button type="button" className="secondary-button" onClick={() => void refresh()}>
          Obnoviť stav
        </button>
      </div>

      <article className={`hero-status status-${system.state}`} aria-live="polite">
        <div>
          <span className="status-dot" aria-hidden="true" />
          <p className="eyebrow">Celkový stav</p>
          <h2>{statusLabel}</h2>
        </div>
        <p>
          {system.state === 'ready' && 'API aj PostgreSQL odpovedajú správne.'}
          {system.state === 'loading' && 'Prebieha kontrola závislostí.'}
          {system.state === 'degraded' && 'API žije, ale databáza ešte nie je pripravená.'}
          {system.state === 'offline' && 'API sa nepodarilo kontaktovať.'}
        </p>
      </article>

      {duplicateProcess && (
        <div className="desk-warning" role="alert">
          Zistených je viac aktívnych inštancií: bot {botInstances}, worker {workerInstances}.
          Automatické publikovanie treba pozastaviť, kým nebude bežať práve jedna z každej.
        </div>
      )}

      <div className="status-grid">
        <article className="status-card">
          <p className="card-label">API proces</p>
          <strong>{system.live ? 'Živý' : 'Bez odpovede'}</strong>
          <span>Verzia {system.live?.version ?? '—'}</span>
        </article>
        <article className="status-card">
          <p className="card-label">PostgreSQL</p>
          <strong>{system.ready?.dependencies.database?.status ?? 'Neznámy stav'}</strong>
          <span>Rozhoduje o pripravenosti API</span>
        </article>
        <article className="status-card">
          <p className="card-label">Discord bot</p>
          <strong>{bot?.healthy ? 'Pripojený' : 'Bez čerstvého spojenia'}</strong>
          <span>
            {instanceCountLabel(botInstances)} · heartbeat {dateTime(bot?.last_seen_at)}
          </span>
        </article>
        <article className="status-card">
          <p className="card-label">Worker</p>
          <strong>{worker?.healthy ? 'Beží' : 'Bez čerstvého heartbeat-u'}</strong>
          <span>
            {instanceCountLabel(workerInstances)} · režim{' '}
            {String(worker?.details.publication_execution_mode ?? 'neznámy')}
          </span>
        </article>
        <article className="status-card">
          <p className="card-label">Najbližší termín</p>
          <strong>{dateTime(system.operations?.next_publication.scheduled_for)}</strong>
          <span>{system.live?.environment ?? 'neznáme prostredie'}</span>
        </article>
      </div>

      <div className="status-grid" aria-label="Metriky publikovania">
        <article className="status-card">
          <p className="card-label">Úspešné publikácie</p>
          <strong>{metrics?.successful ?? '—'}</strong>
          <span>Z posledných {metrics?.sample_size ?? 0} behov</span>
        </article>
        <article className="status-card">
          <p className="card-label">Neúspešné alebo čiastočné</p>
          <strong>{metrics?.failed ?? '—'}</strong>
          <span>Rozpracované: {metrics?.in_progress ?? 0}</span>
        </article>
        <article className="status-card">
          <p className="card-label">Preskočené po ručnom behu</p>
          <strong>{metrics?.skipped ?? '—'}</strong>
          <span>Idempotentne vybavené termíny</span>
        </article>
      </div>

      <section className="dashboard-panel" aria-labelledby="calendar-health-title">
        <header className="dashboard-panel-header">
          <div>
            <p className="eyebrow">Google integrácia</p>
            <h2 id="calendar-health-title">Kalendáre</h2>
          </div>
        </header>
        {system.operations?.calendars.length ? (
          <div className="settings-list">
            {system.operations.calendars.map((calendar) => (
              <article className="settings-row" key={calendar.id}>
                <div>
                  <strong>{calendar.display_name}</strong>
                  <p>
                    {calendar.active ? 'Aktívny' : 'Pozastavený'} · posledný úspech{' '}
                    {dateTime(calendar.last_sync_success_at)}
                  </p>
                </div>
                <span className="status-badge">{calendar.sync_status}</span>
              </article>
            ))}
          </div>
        ) : (
          <p className="dashboard-empty-copy">Nie je pripojený žiadny Google kalendár.</p>
        )}
      </section>

      <section className="dashboard-panel" aria-labelledby="recent-tasks-title">
        <header className="dashboard-panel-header">
          <div>
            <p className="eyebrow">Prevádzková stopa</p>
            <h2 id="recent-tasks-title">Posledné úlohy</h2>
          </div>
        </header>
        {system.operations?.recent_tasks.length ? (
          <div className="settings-list">
            {system.operations.recent_tasks.map((task) => (
              <article className="settings-row" key={task.id}>
                <div>
                  <strong>{task.task_type}</strong>
                  <p>Naplánované {dateTime(task.scheduled_for)}</p>
                </div>
                <span className="status-badge">{task.state}</span>
              </article>
            ))}
          </div>
        ) : (
          <p className="dashboard-empty-copy">Zatiaľ nebola zaznamenaná integračná úloha.</p>
        )}
      </section>

      {system.correlationId && (
        <p className="support-note">
          Referencia chyby: <code>{system.correlationId}</code>
        </p>
      )}
    </section>
  )
}
