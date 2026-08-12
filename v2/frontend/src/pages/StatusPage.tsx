import { useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, CheckCircle2, RefreshCw, ServerCrash } from 'lucide-react'

import {
  ApiError,
  getLiveness,
  getOperationsSummary,
  getReadiness,
  type LivenessResponse,
  type OperationsSummary,
  type ReadinessResponse,
} from '../api/client'
import { Button } from '../components/ui/button'

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
  const [live, ready, operations] = await Promise.allSettled([
    getLiveness(signal),
    getReadiness(signal),
    getOperationsSummary(signal),
  ])
  if (live.status === 'rejected') {
    return {
      state: 'offline',
      live: null,
      ready: null,
      operations: null,
      correlationId: correlationId(live.reason),
    }
  }
  const readiness = ready.status === 'fulfilled' ? ready.value : null
  const summary = operations.status === 'fulfilled' ? operations.value : null
  const botCount = summary?.active_instance_counts.bot ?? 0
  const workerCount = summary?.active_instance_counts.worker ?? 0
  const worker = summary?.processes.find((process) => process.process_name === 'worker')
  const executionMode = String(worker?.details.publication_execution_mode ?? 'unknown')
  const incomplete =
    readiness?.status !== 'ready' ||
    summary === null ||
    botCount !== 1 ||
    workerCount !== 1 ||
    executionMode !== 'live' ||
    summary.processes.some((process) => !process.healthy) ||
    summary.calendars.some(
      (calendar) => calendar.active && !['succeeded', 'running'].includes(calendar.sync_status),
    )
  const reason =
    ready.status === 'rejected'
      ? ready.reason
      : operations.status === 'rejected'
        ? operations.reason
        : null
  return {
    state: incomplete ? 'degraded' : 'ready',
    live: live.value,
    ready: readiness,
    operations: summary,
    correlationId: correlationId(reason),
  }
}

function correlationId(reason: unknown) {
  return reason instanceof ApiError ? reason.correlationId : null
}

function dateTime(value: string | null | undefined): string {
  if (!value) return 'zatiaľ bez údaja'
  return new Intl.DateTimeFormat('sk-SK', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Europe/Bratislava',
  }).format(new Date(value))
}

export function StatusPage() {
  const [system, setSystem] = useState<SystemState>(initialState)
  const refreshInFlight = useRef(false)

  async function refresh() {
    if (refreshInFlight.current) return
    refreshInFlight.current = true
    setSystem((current) => ({ ...current, state: 'loading' }))
    try {
      setSystem(await loadSystemState())
    } finally {
      refreshInFlight.current = false
    }
  }

  useEffect(() => {
    const controller = new AbortController()
    void loadSystemState(controller.signal).then((nextState) => {
      if (!controller.signal.aborted) setSystem(nextState)
    })
    return () => controller.abort()
  }, [])

  const issues = useMemo(() => systemIssues(system), [system])
  const bot = system.operations?.processes.find((process) => process.process_name === 'bot')
  const worker = system.operations?.processes.find((process) => process.process_name === 'worker')
  const executionMode = String(worker?.details.publication_execution_mode ?? 'unknown')
  const metrics = system.operations?.publication_metrics
  const statusCopy = {
    loading: ['Kontrolujem aktuálny stav', 'Carlo práve overuje služby potrebné na publikovanie.'],
    ready: ['Carlo je pripravený', 'Všetky dostupné kontroly potvrdili bežnú prevádzku.'],
    degraded: [
      'Niečo potrebuje pozornosť',
      'Nie všetky kontroly sú v poriadku. Podrobnosti a ďalší krok sú nižšie.',
    ],
    offline: [
      'Carlo je momentálne nedostupný',
      'Aktuálny stav sa nepodarilo získať. Už zobrazené údaje nepovažujte za čerstvé.',
    ],
  }[system.state]

  return (
    <section className="page-stack" aria-labelledby="page-title">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Je Carlo pripravený publikovať?</p>
          <h1 id="page-title">Stav systému</h1>
          <p>Prehľad služieb, ktoré Carlo potrebuje na bezpečnú správu a publikovanie.</p>
        </div>
        <Button
          variant="outline"
          disabled={system.state === 'loading'}
          onClick={() => void refresh()}
        >
          <RefreshCw aria-hidden="true" />
          {system.state === 'loading' ? 'Kontrolujem…' : 'Skontrolovať znova'}
        </Button>
      </header>

      <article className={`hero-status status-${system.state}`} aria-live="polite">
        <div className="system-state-heading">
          {system.state === 'ready' ? (
            <CheckCircle2 aria-hidden="true" />
          ) : system.state === 'offline' ? (
            <ServerCrash aria-hidden="true" />
          ) : (
            <AlertTriangle aria-hidden="true" />
          )}
          <div>
            <p className="eyebrow">Celkový stav</p>
            <h2>{statusCopy[0]}</h2>
          </div>
        </div>
        <p>{statusCopy[1]}</p>
      </article>

      {issues.length > 0 && system.state !== 'loading' && (
        <section className="system-issues" aria-labelledby="system-issues-title" role="alert">
          <h2 id="system-issues-title">Čo treba skontrolovať</h2>
          <ul>
            {issues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
          <p>
            Po náprave použite „Skontrolovať znova“. Automatické publikovanie nezapínajte, kým
            zostáva problém nejasný.
          </p>
        </section>
      )}

      <section aria-labelledby="services-title" className="status-section">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Kľúčové služby</p>
            <h2 id="services-title">Čo Carlo práve dokáže</h2>
          </div>
        </div>
        <div className="status-grid">
          <StatusCard
            title="Webová administrácia"
            value={system.live ? 'Dostupná' : 'Bez čerstvej odpovede'}
            detail={
              system.ready?.status === 'ready'
                ? 'Údaje sa dajú bezpečne čítať a ukladať.'
                : 'Ukladanie nemusí byť momentálne dostupné.'
            }
          />
          <StatusCard
            title="Discord spojenie"
            value={bot?.healthy ? 'Pripojené' : 'Treba skontrolovať'}
            detail={
              bot?.healthy
                ? 'Carlo môže prijímať príkazy a vykonávať Discord operácie.'
                : 'Príkazy alebo Discord operácie nemusia fungovať.'
            }
          />
          <StatusCard
            title="Automatické publikovanie"
            value={publicationModeLabel(worker?.healthy ?? false, executionMode)}
            detail={
              worker?.healthy && executionMode === 'live'
                ? `Najbližší termín: ${dateTime(system.operations?.next_publication?.scheduled_for)}`
                : executionMode === 'shadow'
                  ? 'Carlo pripravuje skúšobné výsledky, ale nič automaticky nezverejní.'
                  : executionMode === 'paused'
                    ? 'Automatické spracovanie je vedome pozastavené.'
                    : 'Plánovaný termín nemusí byť spracovaný.'
            }
          />
        </div>
      </section>

      <section className="dashboard-panel" aria-labelledby="calendar-health-title">
        <header className="dashboard-panel-header">
          <div>
            <p className="eyebrow">Zdroj udalostí</p>
            <h2 id="calendar-health-title">Google kalendáre</h2>
          </div>
        </header>
        {system.operations?.calendars.length ? (
          <div className="settings-list">
            {system.operations.calendars.map((calendar) => (
              <article className="settings-row" key={calendar.id}>
                <div>
                  <strong>{calendar.display_name}</strong>
                  <p>
                    {calendar.active
                      ? `Posledné úspešné obnovenie ${dateTime(calendar.last_sync_success_at)}`
                      : 'Pozastavený – do publikácie sa nepoužíva'}
                  </p>
                </div>
                <span
                  className={`status-pill ${calendar.sync_status === 'succeeded' ? 'status-ready' : calendar.active ? 'status-error' : ''}`}
                >
                  {calendarState(calendar.sync_status, calendar.active)}
                </span>
              </article>
            ))}
          </div>
        ) : (
          <p className="dashboard-empty-copy">
            Carlo funguje aj bez Google kalendára. Udalosti možno pridávať ručne.
          </p>
        )}
      </section>

      <section aria-labelledby="recent-title" className="status-section">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Posledných {metrics?.sample_size ?? '—'} behov</p>
            <h2 id="recent-title">Publikovanie</h2>
          </div>
        </div>
        <div className="status-grid">
          <StatusCard
            title="Úspešné"
            value={metrics ? String(metrics.successful) : '—'}
            detail="Potvrdene dokončené publikácie."
          />
          <StatusCard
            title="Nevykonané alebo čiastočné"
            value={metrics ? String(metrics.failed) : '—'}
            detail={
              metrics
                ? `Práve rozpracované: ${metrics.in_progress}`
                : 'Prevádzkový súhrn nie je dostupný.'
            }
          />
          <StatusCard
            title="Preskočené po ručnom zverejnení"
            value={metrics ? String(metrics.skipped) : '—'}
            detail="Termíny, ktoré Carlo zámerne nezopakoval."
          />
        </div>
      </section>

      <details className="technical-details system-technical-details">
        <summary>Technické údaje pre riešenie problému</summary>
        <dl>
          <div>
            <dt>Verzia</dt>
            <dd>{system.live?.version ?? 'neznáma'}</dd>
          </div>
          <div>
            <dt>Prostredie</dt>
            <dd>{system.live?.environment ?? 'neznáme'}</dd>
          </div>
          <div>
            <dt>Posledná odpoveď Discord procesu</dt>
            <dd>{dateTime(bot?.last_seen_at)}</dd>
          </div>
          <div>
            <dt>Posledná odpoveď plánovača</dt>
            <dd>{dateTime(worker?.last_seen_at)}</dd>
          </div>
          {system.correlationId && (
            <div>
              <dt>Referencia chyby</dt>
              <dd>
                <code>{system.correlationId}</code>
              </dd>
            </div>
          )}
        </dl>
      </details>
    </section>
  )
}

function StatusCard({ title, value, detail }: { title: string; value: string; detail: string }) {
  return (
    <article className="status-card">
      <p className="card-label">{title}</p>
      <strong>{value}</strong>
      <span>{detail}</span>
    </article>
  )
}

function systemIssues(system: SystemState) {
  if (system.state === 'offline')
    return [
      'Webová služba Carla neodpovedá. Skúste kontrolu znova; ak problém trvá, kontaktujte správcu nasadenia.',
    ]
  if (system.state !== 'degraded') return []
  const issues: string[] = []
  if (system.ready?.status !== 'ready')
    issues.push('Databáza alebo iná základná služba nepotvrdila pripravenosť.')
  if (!system.operations)
    issues.push('Prevádzkový súhrn sa nepodarilo načítať; stav Discordu a plánovača je neznámy.')
  const counts = system.operations?.active_instance_counts
  if ((counts?.bot ?? 0) === 0)
    issues.push('Discord proces nie je aktívny. Príkazy a Discord operácie nebudú fungovať.')
  if ((counts?.worker ?? 0) === 0)
    issues.push('Plánovač nie je aktívny. Najbližší termín sa automaticky nespracuje.')
  if ((counts?.bot ?? 0) > 1 || (counts?.worker ?? 0) > 1)
    issues.push(
      'Beží viac procesov rovnakého typu. Automatické publikovanie treba ponechať vypnuté.',
    )
  if (system.operations?.processes.some((process) => !process.healthy))
    issues.push('Discord spojenie alebo plánovač neposlal čerstvé potvrdenie činnosti.')
  const unavailable =
    system.operations?.calendars.filter(
      (calendar) => calendar.active && !['succeeded', 'running'].includes(calendar.sync_status),
    ) ?? []
  if (unavailable.length)
    issues.push(
      `${unavailable.length === 1 ? 'Jeden aktívny kalendár nemá použiteľné údaje' : `${unavailable.length} aktívne kalendáre nemajú použiteľné údaje`}. Budúci obsah môže byť neúplný.`,
    )
  const worker = system.operations?.processes.find((process) => process.process_name === 'worker')
  const mode = String(worker?.details.publication_execution_mode ?? 'unknown')
  if (worker?.healthy && mode === 'shadow')
    issues.push('Carlo je v skúšobnom režime. Automatické výsledky sa na Discord nezverejnia.')
  else if (worker?.healthy && mode === 'paused')
    issues.push('Automatické publikovanie je pozastavené.')
  else if (worker?.healthy && mode !== 'live')
    issues.push('Režim automatického publikovania sa nepodarilo spoľahlivo určiť.')
  return issues
}

function publicationModeLabel(healthy: boolean, mode: string) {
  if (!healthy) return 'Treba skontrolovať'
  if (mode === 'live') return 'Plánovač beží'
  if (mode === 'shadow') return 'Skúšobný režim'
  if (mode === 'paused') return 'Pozastavené'
  return 'Stav neznámy'
}

function calendarState(status: string, active: boolean) {
  if (!active) return 'Pozastavený'
  return (
    (
      {
        succeeded: 'Aktuálny',
        running: 'Obnovuje sa',
        failed: 'Chyba obnovenia',
        never: 'Ešte neobnovený',
      } as Record<string, string>
    )[status] ?? 'Stav neznámy'
  )
}
