import { useMemo, useState } from 'react'

import { getAudit, type AuditRecord } from '../api/client'
import { useApiList } from '../hooks/useApiList'

type AuditFilter = 'all' | 'events' | 'content' | 'security'

export function AuditPage() {
  const { items, loading, error, reload } = useApiList(getAudit)
  const [filter, setFilter] = useState<AuditFilter>('all')
  const filtered = useMemo(
    () => items.filter((item) => matchesFilter(item, filter)),
    [items, filter],
  )

  return (
    <section className="audit-page page-stack" aria-labelledby="audit-title">
      <header className="page-heading">
        <div>
          <p className="eyebrow">História administrácie</p>
          <h1 id="audit-title">Audit</h1>
          <p>Kto, kedy a čo zmenil. Záznamy sú iba na čítanie.</p>
        </div>
        <button className="secondary-button" type="button" onClick={() => void reload()}>
          Obnoviť
        </button>
      </header>

      <div className="filter-bar" aria-label="Filtrovať audit">
        {(
          [
            ['all', 'Všetko'],
            ['events', 'Kalendárové udalosti'],
            ['content', 'Ručný obsah'],
            ['security', 'Prístupy a systém'],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            type="button"
            aria-pressed={filter === value}
            onClick={() => setFilter(value)}
          >
            {label}
          </button>
        ))}
      </div>

      {loading && <AuditState text="Načítavam históriu…" />}
      {error && <AuditState text={error.message} retry={() => void reload()} />}
      {!loading && !error && filtered.length === 0 && (
        <AuditState
          text={
            items.length ? 'Tomuto filtru nezodpovedá žiadna zmena.' : 'Audit je zatiaľ prázdny.'
          }
        />
      )}
      {!loading && !error && filtered.length > 0 && (
        <div className="audit-timeline">
          {filtered.map((item) => (
            <AuditEntry item={item} key={item.id} />
          ))}
        </div>
      )}
    </section>
  )
}

function AuditEntry({ item }: { item: AuditRecord }) {
  const changes = summarizeChanges(item.before, item.after)
  return (
    <article className="audit-entry">
      <div
        className={`audit-marker ${item.result === 'failed' ? 'audit-failed' : ''}`}
        aria-hidden="true"
      />
      <div className="audit-card">
        <div className="audit-card-heading">
          <div>
            <span className="audit-object">{objectLabel(item.object_type)}</span>
            <h2>{actionLabel(item.action)}</h2>
          </div>
          <span
            className={`status-pill ${item.result === 'succeeded' ? 'status-ready' : 'status-error'}`}
          >
            {item.result === 'succeeded' ? 'Úspešné' : 'Zamietnuté'}
          </span>
        </div>
        <p className="audit-meta">
          {formatDateTime(item.created_at)} ·{' '}
          {item.actor_user_id ? `Používateľ ${item.actor_user_id}` : 'Systém'}
        </p>
        {changes.length > 0 && (
          <ul className="change-list">
            {changes.map((change) => (
              <li key={change}>{change}</li>
            ))}
          </ul>
        )}
        <details className="audit-details">
          <summary>Prevádzkové údaje</summary>
          <dl>
            <div>
              <dt>Objekt</dt>
              <dd>{item.object_id}</dd>
            </div>
            <div>
              <dt>Korelačné ID</dt>
              <dd>{item.correlation_id}</dd>
            </div>
          </dl>
        </details>
      </div>
    </article>
  )
}

function matchesFilter(item: AuditRecord, filter: AuditFilter) {
  if (filter === 'all') return true
  if (filter === 'events')
    return ['event_override', 'event_series_override'].includes(item.object_type)
  if (filter === 'content') return ['manual_event', 'info_announcement'].includes(item.object_type)
  return !['event_override', 'event_series_override', 'manual_event', 'info_announcement'].includes(
    item.object_type,
  )
}

const fieldLabels: Record<string, string> = {
  public_title: 'titulok',
  public_description: 'popis',
  description_state: 'spôsob popisu',
  inclusion_decision: 'zaradenie',
  title: 'názov',
  description: 'popis',
  active: 'aktivita',
  valid_from: 'platnosť od',
  valid_until: 'platnosť do',
  starts_at: 'začiatok',
  starts_on: 'deň začiatku',
}

function summarizeChanges(
  before: Record<string, unknown> | null,
  after: Record<string, unknown> | null,
) {
  if (!after) return before ? ['Záznam bol odstránený.'] : []
  if (!before) return ['Vznikol nový záznam.']
  return Object.keys(fieldLabels)
    .filter((key) => JSON.stringify(before[key]) !== JSON.stringify(after[key]))
    .slice(0, 4)
    .map((key) => `Zmenené pole: ${fieldLabels[key]}`)
}

function objectLabel(value: string) {
  return (
    (
      {
        event_override: 'Kalendárová udalosť',
        event_series_override: 'Séria udalostí',
        manual_event: 'Manuálna udalosť',
        info_announcement: 'INFO oznam',
        web_session: 'Webová relácia',
      } as Record<string, string>
    )[value] ?? 'Systém'
  )
}

function actionLabel(action: string) {
  if (action.endsWith('.created')) return 'Záznam bol vytvorený'
  if (action.endsWith('.updated')) return 'Záznam bol upravený'
  if (action.endsWith('.deleted')) return 'Záznam bol odstránený'
  if (action.endsWith('_denied')) return 'Pokus o zmenu bol zamietnutý'
  return action.replaceAll('_', ' ').replaceAll('.', ' · ')
}

function formatDateTime(value: string | null) {
  if (!value) return 'Čas nie je dostupný'
  return new Intl.DateTimeFormat('sk-SK', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Europe/Bratislava',
  }).format(new Date(value))
}

function AuditState({ text, retry }: { text: string; retry?: () => void }) {
  return (
    <div className="content-empty" role="status">
      <strong>{text}</strong>
      {retry && <button onClick={retry}>Skúsiť znova</button>}
    </div>
  )
}
