import { useMemo, useRef, useState } from 'react'
import { AlertTriangle, CheckCircle2, ExternalLink, Eye, Radio } from 'lucide-react'

import {
  confirmPublicationMessageNotSent,
  getPublicationHistory,
  getShadowPublicationHistory,
  linkExistingPublicationMessage,
  type PublicationHistoryEntry,
  type PublicationDraft,
  type ShadowPublicationCapture,
} from '../api/client'
import { useAuth } from '../auth/context'
import { DiscordPreview } from '../components/DiscordPreview'
import { EmptyState, LoadErrorState, LoadingState } from '../components/AsyncState'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { useApiList } from '../hooks/useApiList'

export function PublicationHistoryPage() {
  const auth = useAuth()
  const published = useApiList(getPublicationHistory)
  const shadow = useApiList(getShadowPublicationHistory)
  const [filter, setFilter] = useState<'all' | 'automatic' | 'manual' | 'attention'>('all')
  const visiblePublished = useMemo(
    () =>
      published.items.filter((entry) => {
        if (filter === 'all') return true
        if (filter === 'attention') return needsAttention(entry.state)
        return entry.mode === filter
      }),
    [filter, published.items],
  )
  const reload = () => Promise.all([published.reload(), shadow.reload()])
  return (
    <section className="history-page page-stack" aria-labelledby="history-title">
      <header className="page-heading history-heading">
        <div>
          <p className="eyebrow">Čo sa naozaj zverejnilo</p>
          <h1 id="history-title">História publikácií</h1>
          <p>Presne to, čo Carlo skutočne pripravil a odoslal do Discordu.</p>
        </div>
        <Button variant="outline" onClick={() => void reload()}>
          Obnoviť
        </Button>
      </header>
      <div className="history-filter-row">
        <div className="filter-bar" aria-label="Filtrovať publikácie">
          {(
            [
              ['all', 'Všetky'],
              ['automatic', 'Automatické'],
              ['manual', 'Ručné'],
              ['attention', 'Potrebujú pozornosť'],
            ] as const
          ).map(([value, label]) => (
            <button
              type="button"
              aria-pressed={filter === value}
              onClick={() => setFilter(value)}
              key={value}
            >
              {label}
            </button>
          ))}
        </div>
        {!published.loading && !published.error && (
          <p className="filtered-count" aria-live="polite">
            {visiblePublished.length} z {published.items.length} načítaných publikácií
          </p>
        )}
      </div>
      <section className="history-section" aria-labelledby="published-history-title">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Odoslané správy</p>
            <h2 id="published-history-title">Publikácie</h2>
          </div>
        </div>
        {published.loading && <LoadingState label="Načítavam publikácie…" />}
        {published.error && (
          <LoadErrorState
            detail={published.error.message}
            onRetry={() => void published.reload()}
          />
        )}
        {!published.loading && !published.error && published.items.length === 0 && (
          <EmptyState
            title="Zatiaľ sa nič nezverejnilo"
            detail="Po prvom ručnom alebo automatickom zverejnení tu nájdete presný výsledok."
          />
        )}
        {!published.loading &&
          !published.error &&
          published.items.length > 0 &&
          visiblePublished.length === 0 && (
            <EmptyState
              title="Tomuto filtru nič nezodpovedá"
              detail="Zrušte filter alebo vyberte inú skupinu publikácií."
              action={
                <Button variant="outline" onClick={() => setFilter('all')}>
                  Zobraziť všetky
                </Button>
              }
            />
          )}
        {!published.loading && !published.error && visiblePublished.length > 0 && (
          <div className="publication-history-list">
            {visiblePublished.map((entry) => (
              <HistoryRun
                entry={entry}
                canRecover={
                  auth.status === 'authenticated' &&
                  auth.session.capabilities.includes('reconcile_publication')
                }
                onRecovered={() => void published.reload()}
                key={entry.id}
              />
            ))}
          </div>
        )}
      </section>
      <section className="history-section history-checks" aria-labelledby="shadow-history-title">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Bez odoslania do Discordu</p>
            <h2 id="shadow-history-title">Kontrolné náhľady</h2>
            <p>Automatické skúšky pripraveného obsahu. Na Discord sa nič neodoslalo.</p>
          </div>
          <Badge variant="outline">Kontrola pred spustením</Badge>
        </div>
        {shadow.loading && <LoadingState label="Načítavam kontrolné náhľady…" />}
        {shadow.error && (
          <LoadErrorState detail={shadow.error.message} onRetry={() => void shadow.reload()} />
        )}
        {!shadow.loading && !shadow.error && shadow.items.length === 0 && (
          <EmptyState
            title="Zatiaľ bez kontrolného náhľadu"
            detail="Carlo ešte nezachytil žiadny plánovaný termín v kontrolnom režime."
          />
        )}
        {!shadow.loading && !shadow.error && shadow.items.length > 0 && (
          <div className="publication-history-list">
            {shadow.items.map((capture) => (
              <ShadowRun capture={capture} key={capture.id} />
            ))}
          </div>
        )}
      </section>
    </section>
  )
}

function ShadowRun({ capture }: { capture: ShadowPublicationCapture }) {
  return (
    <Card className="history-run shadow-run">
      <CardHeader className="history-run-header">
        <div className="history-state-icon shadow">
          <Eye />
        </div>
        <div>
          <CardTitle>{formatDate(capture.scheduled_for)}</CardTitle>
          <CardDescription>
            Posledná kontrola {formatDate(capture.last_observed_at)} · bez Discord odoslania
          </CardDescription>
        </div>
        <Badge variant={capture.calendar_sync_valid ? 'secondary' : 'destructive'}>
          {capture.calendar_sync_valid ? 'Kontrola je úplná' : 'Neúplné kalendáre'}
        </Badge>
      </CardHeader>
      <CardContent>
        {!capture.calendar_sync_valid && (
          <p className="desk-warning" role="alert">
            Niektorý aktívny kalendár sa neobnovil. Tento náhľad preto nemožno považovať za
            spoľahlivú kontrolu budúcej publikácie.
          </p>
        )}
        <div className="history-metrics">
          <span>
            <strong>{capture.item_count}</strong> položiek
          </span>
          <span>
            <strong>{capture.message_count}</strong> správ
          </span>
          <span>
            <strong>{capture.observation_count}</strong> kontrol
          </span>
        </div>
        <details className="history-details">
          <summary>Zobraziť pripravený obsah</summary>
          <div className="history-snapshot">
            {capture.draft.intro_text && (
              <p className="history-intro">{capture.draft.intro_text}</p>
            )}
            {capture.draft.public_items.map((item) => (
              <article key={`${item.kind}-${item.source_id}`}>
                <small>{item.display_time ?? kindLabel(item.kind)}</small>
                <strong>{item.title}</strong>
                {item.description && <p>{item.description}</p>}
              </article>
            ))}
          </div>
        </details>
        <details className="technical-details">
          <summary>Technické údaje</summary>
          <p className="shadow-hash">
            Kontrolný odtlačok <code>{capture.draft_sha256.slice(0, 16)}</code>
          </p>
        </details>
      </CardContent>
    </Card>
  )
}

function HistoryRun({
  entry,
  canRecover,
  onRecovered,
}: {
  entry: PublicationHistoryEntry
  canRecover: boolean
  onRecovered: () => void
}) {
  const successful = entry.state.startsWith('succeeded')
  const attention = needsAttention(entry.state)
  const uncertain = entry.messages.filter((message) => message.state === 'uncertain')
  return (
    <Card className="history-run" id={`run-${entry.id}`}>
      <CardHeader className="history-run-header">
        <div
          className={`history-state-icon ${successful ? 'success' : attention ? 'warning' : 'shadow'}`}
        >
          {successful ? <CheckCircle2 /> : attention ? <AlertTriangle /> : <Eye />}
        </div>
        <div>
          <CardTitle>{formatDate(entry.scheduled_for)}</CardTitle>
          <CardDescription>
            {entry.mode === 'manual' ? 'Ručné publikovanie' : 'Automatické publikovanie'} ·{' '}
            {entry.completed_at ? `dokončené ${formatDate(entry.completed_at)}` : 'nedokončené'}
          </CardDescription>
        </div>
        <Badge variant={successful ? 'secondary' : 'outline'}>{stateLabel(entry.state)}</Badge>
      </CardHeader>
      <CardContent>
        <div className="history-metrics">
          <span>
            <strong>{entry.items.length}</strong> položiek
          </span>
          <span>
            <strong>{entry.messages.length}</strong> správ
          </span>
          <span>
            <strong>{entry.attempt}</strong> pokus
          </span>
        </div>
        <details className="history-details">
          <summary>Zobraziť presný Discord výstup</summary>
          <DiscordPreview draft={historyDraft(entry)} />
        </details>
        <div className="history-message-links">
          {entry.messages.map((message) =>
            message.jump_url ? (
              <a href={message.jump_url} target="_blank" rel="noreferrer" key={message.id}>
                <Radio /> Správa {message.position + 1} <ExternalLink />
              </a>
            ) : (
              <span key={message.id}>
                Správa {message.position + 1}: {stateLabel(message.state)}
              </span>
            ),
          )}
        </div>
        {entry.messages
          .filter((message) => message.reaction_error)
          .map((message) => (
            <p className="history-error" key={`reaction-${message.id}`}>
              Seen reakciu sa pri správe {message.position + 1} nepodarilo pridať. Samotná správa
              bola odoslaná.
            </p>
          ))}
        {canRecover && uncertain.length > 0 && (
          <section className="history-recovery" aria-label="Obnova publikovania">
            <strong>Publikovanie potrebuje rozhodnutie Admina</strong>
            <p>
              Najprv na Discorde overte, či neistá správa skutočne vznikla. Carlo potom bezpečne
              pokračuje od nasledujúcej časti.
            </p>
            {uncertain.map((message) => (
              <RecoveryMessage
                runId={entry.id}
                position={message.position}
                onRecovered={onRecovered}
                key={message.id}
              />
            ))}
          </section>
        )}
        {entry.error_detail && <p className="history-error">{entry.error_detail}</p>}
      </CardContent>
    </Card>
  )
}

function RecoveryMessage({
  runId,
  position,
  onRecovered,
}: {
  runId: string
  position: number
  onRecovered: () => void
}) {
  const [messageId, setMessageId] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inFlight = useRef(false)

  async function linkExisting() {
    if (inFlight.current) return
    if (!/^\d+$/.test(messageId)) {
      setError('Zadajte číselné ID správy z Discordu.')
      return
    }
    inFlight.current = true
    setBusy(true)
    setError(null)
    try {
      await linkExistingPublicationMessage(runId, position, messageId)
      onRecovered()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Obnova publikovania zlyhala.')
    } finally {
      inFlight.current = false
      setBusy(false)
    }
  }

  async function confirmNotSent() {
    if (inFlight.current) return
    inFlight.current = true
    setBusy(true)
    setError(null)
    try {
      await confirmPublicationMessageNotSent(runId, position)
      onRecovered()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Obnova publikovania zlyhala.')
    } finally {
      inFlight.current = false
      setBusy(false)
    }
  }

  return (
    <div className="history-recovery-message">
      <p>Neistá správa {position + 1}</p>
      <div>
        <Input
          inputMode="numeric"
          value={messageId}
          onChange={(event) => setMessageId(event.target.value.trim())}
          placeholder="Discord ID existujúcej správy"
          aria-label={`Discord ID správy ${position + 1}`}
        />
        <Button disabled={busy || !messageId} onClick={() => void linkExisting()}>
          Prepojiť existujúcu správu
        </Button>
      </div>
      <details>
        <summary>Správa na Discorde nevznikla</summary>
        <p>Túto voľbu použite až po kontrole kanála. Carlo túto časť odošle znova.</p>
        <Button variant="outline" disabled={busy} onClick={() => void confirmNotSent()}>
          Potvrdiť, že nebola odoslaná
        </Button>
      </details>
      {error && <p className="history-error">{error}</p>}
    </div>
  )
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('sk-SK', {
    dateStyle: 'long',
    timeStyle: 'short',
    timeZone: 'Europe/Bratislava',
  }).format(new Date(value))
}

function stateLabel(value: string) {
  return (
    {
      succeeded_automatic: 'Úspešné',
      succeeded_manual: 'Úspešné',
      partially_published: 'Čiastočné',
      retry_pending: 'Čaká na opakovanie',
      uncertain: 'Vyžaduje kontrolu',
      failed: 'Zlyhané',
      preparing: 'Pripravuje sa',
      publishing: 'Zverejňuje sa',
      skipped_after_manual: 'Preskočené po ručnom zverejnení',
      sent: 'Odoslaná',
      pending: 'Čaká',
      sending: 'Odosiela sa',
    }[value] ?? value.replaceAll('_', ' ')
  )
}

function needsAttention(value: string) {
  return ['partially_published', 'retry_pending', 'failed', 'uncertain'].includes(value)
}

function historyDraft(entry: PublicationHistoryEntry): PublicationDraft {
  const scheduledLocal = new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Europe/Bratislava',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
    .format(new Date(entry.scheduled_for))
    .replace(' ', 'T')
  return {
    composer_version: entry.composer_version,
    guild_id: 0,
    slot_key: entry.slot_key,
    scheduled_for: entry.scheduled_for,
    scheduled_local: scheduledLocal,
    timezone: 'Europe/Bratislava',
    window_starts_at: entry.scheduled_for,
    window_ends_at: entry.scheduled_for,
    intro_text: entry.intro_text,
    outro_text: entry.outro_text,
    editor_events: [],
    public_items: entry.items.map((item) => ({
      kind: item.kind,
      source_id: item.id,
      title: item.title ?? 'Bez názvu',
      description: item.description,
      included: true,
      exclusion_reason: null,
      display_time: item.display_time,
      day_name: null,
      day_emoji: item.day_emoji,
      is_all_day: Boolean(item.is_all_day),
      source_title: item.title ?? 'Bez názvu',
      source_description: item.description,
      is_recurring: false,
      instance_override_version: 0,
      instance_public_title: null,
      instance_description_state: 'inherit',
      instance_public_description: null,
      inclusion_decision: 'auto',
      series_override_version: 0,
      series_public_title: null,
      series_description_state: 'inherit',
      series_public_description: null,
    })),
    warnings: [],
    messages: entry.messages.map((message) => ({
      position: message.position,
      part_key: message.id,
      content: message.content,
      embeds: message.embeds,
      allowed_mentions: message.allowed_mentions,
      seen_target: message.seen_target,
      reaction_emoji: message.reaction_emoji,
    })),
  }
}

function kindLabel(value: string) {
  if (value === 'info') return 'INFO oznam'
  if (value === 'manual_event') return 'Manuálna udalosť'
  return 'Kalendárová udalosť'
}
