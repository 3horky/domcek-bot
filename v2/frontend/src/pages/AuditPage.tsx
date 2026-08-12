import { useMemo, useState } from 'react'
import { CheckCircle2, CircleX, RefreshCw } from 'lucide-react'

import { getAudit, type AuditRecord } from '../api/client'
import { useAuth } from '../auth/context'
import { EmptyState, LoadErrorState, LoadingState } from '../components/AsyncState'
import { Button } from '../components/ui/button'
import { useApiList } from '../hooks/useApiList'

type AuditFilter = 'all' | 'events' | 'content' | 'server' | 'failed'

export function AuditPage() {
  const auth = useAuth()
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
          <p className="eyebrow">Kto, kedy a čo zmenil</p>
          <h1 id="audit-title">História zmien</h1>
          <p>Zmeny obsahu, nastavení a servera na jednom mieste. Záznamy sa nedajú upravovať.</p>
        </div>
        <Button variant="outline" onClick={() => void reload()}>
          <RefreshCw aria-hidden="true" /> Obnoviť
        </Button>
      </header>

      <div className="audit-filter-row">
        <div className="filter-bar" aria-label="Filtrovať históriu zmien">
          {(
            [
              ['all', 'Všetko'],
              ['events', 'Kalendár'],
              ['content', 'Vlastný obsah'],
              ['server', 'Server a nastavenia'],
              ['failed', 'Nevykonané'],
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
        {!loading && !error && (
          <p className="filtered-count" aria-live="polite">
            {filtered.length} zo {items.length} načítaných zmien
          </p>
        )}
      </div>

      {loading && <LoadingState label="Načítavam históriu zmien…" />}
      {error && <LoadErrorState detail={error.message} onRetry={() => void reload()} />}
      {!loading && !error && items.length === 0 && (
        <EmptyState
          title="Zatiaľ bez zaznamenanej zmeny"
          detail="Po prvej úprave obsahu, nastavení alebo Discord servera sa tu objaví dohľadateľný záznam."
        />
      )}
      {!loading && !error && items.length > 0 && filtered.length === 0 && (
        <EmptyState
          title="Tomuto filtru nič nezodpovedá"
          detail="Zrušte filter alebo vyberte inú skupinu zmien."
          action={
            <Button variant="outline" onClick={() => setFilter('all')}>
              Zobraziť všetko
            </Button>
          }
        />
      )}
      {!loading && !error && filtered.length > 0 && (
        <div className="audit-list">
          {filtered.map((item) => (
            <AuditEntry
              item={item}
              currentUser={
                auth.status === 'authenticated'
                  ? { id: auth.session.user.id, name: auth.session.user.display_name }
                  : null
              }
              key={item.id}
            />
          ))}
        </div>
      )}
    </section>
  )
}

function AuditEntry({
  item,
  currentUser,
}: {
  item: AuditRecord
  currentUser: { id: string; name: string } | null
}) {
  const description = describeChange(item)
  const actor =
    item.actor_user_id === null
      ? 'Carlo'
      : item.actor_user_id === currentUser?.id
        ? `${currentUser.name} (vy)`
        : 'Iný správca'
  return (
    <article className={`audit-row ${item.result === 'failed' ? 'audit-row-failed' : ''}`}>
      <div className="audit-result-icon" aria-hidden="true">
        {item.result === 'succeeded' ? <CheckCircle2 /> : <CircleX />}
      </div>
      <div className="audit-row-copy">
        <div className="audit-card-heading">
          <div>
            <p className="audit-object">{objectLabel(item.object_type)}</p>
            <h2>{description.title}</h2>
          </div>
          <span
            className={`status-pill ${item.result === 'succeeded' ? 'status-ready' : 'status-error'}`}
          >
            {item.result === 'succeeded' ? 'Vykonané' : 'Nevykonané'}
          </span>
        </div>
        <p className="audit-meta">
          <span>{actor}</span>
          <time dateTime={item.created_at ?? undefined}>{formatDateTime(item.created_at)}</time>
        </p>
        <p className="audit-summary">{description.summary}</p>
        {description.changes.length > 0 && (
          <ul className="change-list">
            {description.changes.map((change) => (
              <li key={change}>{change}</li>
            ))}
          </ul>
        )}
        <details className="audit-details">
          <summary>Technické údaje</summary>
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
  if (filter === 'failed') return item.result === 'failed'
  if (filter === 'events')
    return ['event_override', 'event_series_override'].includes(item.object_type)
  if (filter === 'content') return ['manual_event', 'info_announcement'].includes(item.object_type)
  return !['event_override', 'event_series_override', 'manual_event', 'info_announcement'].includes(
    item.object_type,
  )
}

const fieldLabels: Record<string, string> = {
  public_title: 'Titulok',
  public_description: 'Popis',
  description_state: 'Použitie popisu',
  inclusion_decision: 'Zaradenie do oznamov',
  title: 'Názov',
  description: 'Popis',
  active: 'Aktívnosť',
  valid_from: 'Platnosť od',
  valid_until: 'Platnosť do',
  starts_at: 'Začiatok',
  starts_on: 'Deň začiatku',
  publication_weekday: 'Deň publikovania',
  publication_time: 'Čas publikovania',
  automatic_publication_enabled: 'Automatické publikovanie',
  display_name: 'Názov kalendára',
  role: 'Rola',
}

function describeChange(item: AuditRecord) {
  const action = actionLabel(item.action)
  const object = objectName(item)
  if (item.result === 'failed') {
    return {
      title: action.failedTitle,
      summary: object
        ? `Zmena sa nevykonala. ${object} zostal bez potvrdenej zmeny.`
        : 'Zmena sa nevykonala a Carlo nepotvrdzuje žiadny externý účinok.',
      changes: summarizeChanges(item.before, item.after),
    }
  }
  return {
    title: action.title,
    summary: action.summary(object),
    changes: summarizeChanges(item.before, item.after),
  }
}

function summarizeChanges(
  before: Record<string, unknown> | null,
  after: Record<string, unknown> | null,
) {
  if (!after || !before) return []
  return Object.keys(fieldLabels)
    .filter((key) => JSON.stringify(before[key]) !== JSON.stringify(after[key]))
    .slice(0, 5)
    .map((key) => `${fieldLabels[key]}: ${valueLabel(before[key])} → ${valueLabel(after[key])}`)
}

function valueLabel(value: unknown) {
  if (value === null || value === undefined || value === '') return 'bez hodnoty'
  if (value === true) return 'zapnuté'
  if (value === false) return 'vypnuté'
  const text = String(value)
  return text.length > 72 ? `${text.slice(0, 69)}…` : text
}

function objectName(item: AuditRecord) {
  const value = item.after ?? item.before
  if (!value) return ''
  const name = value.title ?? value.display_name ?? value.original_channel_name
  return typeof name === 'string' && name.trim() ? `„${name}“` : ''
}

function objectLabel(value: string) {
  return (
    (
      {
        event_override: 'Kalendárová udalosť',
        event_series_override: 'Séria udalostí',
        manual_event: 'Manuálna udalosť',
        info_announcement: 'INFO oznam',
        web_session: 'Prihlásenie',
        discord_member: 'Oprávnenie človeka',
        discord_channel: 'Discord kanál',
        channel_archive_request: 'Archivácia kanála',
        calendar_source: 'Google kalendár',
        publication_settings: 'Publikovanie',
        reaction_settings: 'Reakcie',
        publication_run: 'Publikácia',
      } as Record<string, string>
    )[value] ?? 'Systémová zmena'
  )
}

function actionLabel(action: string) {
  if (action.includes('role.') && action.endsWith('assigned'))
    return actionText(
      'Rola bola udelená',
      'Rolu sa nepodarilo udeliť',
      (object) => `${object || 'Vybraný človek'} dostal nové oprávnenie.`,
    )
  if (action.includes('role.') && action.endsWith('removed'))
    return actionText(
      'Rola bola odobraná',
      'Rolu sa nepodarilo odobrať',
      (object) => `${object || 'Vybranému človeku'} bolo odobrané oprávnenie.`,
    )
  if (action.endsWith('created'))
    return actionText(
      'Záznam bol vytvorený',
      'Záznam sa nepodarilo vytvoriť',
      (object) => `${object || 'Nový záznam'} bol vytvorený.`,
    )
  if (action.endsWith('updated'))
    return actionText(
      'Záznam bol upravený',
      'Záznam sa nepodarilo upraviť',
      (object) => `${object || 'Záznam'} bol upravený.`,
    )
  if (action.endsWith('deleted'))
    return actionText(
      'Záznam bol odstránený',
      'Záznam sa nepodarilo odstrániť',
      (object) => `${object || 'Záznam'} bol odstránený.`,
    )
  if (action.includes('archive'))
    return actionText(
      'Archivácia bola zaznamenaná',
      'Archivácia sa nevykonala',
      (object) => `${object || 'Kanál'} prešiel archivačným krokom.`,
    )
  if (action.includes('publication'))
    return actionText(
      'Publikačný krok bol dokončený',
      'Publikačný krok zlyhal',
      () => 'Carlo zaznamenal výsledok publikačného kroku.',
    )
  if (action.endsWith('denied') || action.endsWith('_denied'))
    return actionText(
      'Pokus bol zamietnutý',
      'Pokus bol zamietnutý',
      () => 'Bezpečnostné pravidlo zabránilo zmene.',
    )
  return actionText(
    'Zmena bola zaznamenaná',
    'Zmenu sa nepodarilo vykonať',
    (object) => `${object || 'Zmena'} bola zaznamenaná.`,
  )
}

function actionText(title: string, failedTitle: string, summary: (object: string) => string) {
  return { title, failedTitle, summary }
}

function formatDateTime(value: string | null) {
  if (!value) return 'Čas nie je dostupný'
  return new Intl.DateTimeFormat('sk-SK', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Europe/Bratislava',
  }).format(new Date(value))
}
