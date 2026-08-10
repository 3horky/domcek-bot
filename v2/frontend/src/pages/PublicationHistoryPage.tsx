import { useState } from 'react'
import { AlertTriangle, CheckCircle2, ExternalLink, Eye, History, Radio } from 'lucide-react'

import {
  confirmPublicationMessageNotSent,
  getPublicationHistory,
  getShadowPublicationHistory,
  linkExistingPublicationMessage,
  type PublicationHistoryEntry,
  type ShadowPublicationCapture,
} from '../api/client'
import { useAuth } from '../auth/context'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { useApiList } from '../hooks/useApiList'

export function PublicationHistoryPage() {
  const auth = useAuth()
  const published = useApiList(getPublicationHistory)
  const shadow = useApiList(getShadowPublicationHistory)
  const reload = () => Promise.all([published.reload(), shadow.reload()])
  return (
    <section className="history-page page-stack" aria-labelledby="history-title">
      <header className="page-heading history-heading">
        <div>
          <p className="eyebrow">Nemenný výstup</p>
          <h1 id="history-title">História publikácií</h1>
          <p>Presne to, čo Carlo skutočne pripravil a odoslal do Discordu.</p>
        </div>
        <Button variant="outline" onClick={() => void reload()}>
          Obnoviť
        </Button>
      </header>
      <section className="history-section" aria-labelledby="shadow-history-title">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Bez odoslania do Discordu</p>
            <h2 id="shadow-history-title">Tieňová prevádzka</h2>
          </div>
          <Badge variant="outline">E12 kontrola</Badge>
        </div>
        {shadow.loading && <HistoryState text="Načítavam tieňové kontroly…" />}
        {shadow.error && (
          <HistoryState text={shadow.error.message} retry={() => void shadow.reload()} />
        )}
        {!shadow.loading && !shadow.error && shadow.items.length === 0 && (
          <HistoryState text="Tieňový worker ešte nezachytil žiadny publikačný termín." />
        )}
        {!shadow.loading && !shadow.error && shadow.items.length > 0 && (
          <div className="publication-history-list">
            {shadow.items.map((capture) => (
              <ShadowRun capture={capture} key={capture.id} />
            ))}
          </div>
        )}
      </section>
      <section className="history-section" aria-labelledby="published-history-title">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Odoslané správy</p>
            <h2 id="published-history-title">Skutočné publikácie</h2>
          </div>
        </div>
        {published.loading && <HistoryState text="Načítavam publikácie…" />}
        {published.error && (
          <HistoryState text={published.error.message} retry={() => void published.reload()} />
        )}
        {!published.loading && !published.error && published.items.length === 0 && (
          <HistoryState text="Carlo ešte nemá uloženú žiadnu publikáciu." />
        )}
        {!published.loading && !published.error && published.items.length > 0 && (
          <div className="publication-history-list">
            {published.items.map((entry) => (
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
          {capture.calendar_sync_valid ? 'Platný tieňový dôkaz' : 'Neplatný sync dôkaz'}
        </Badge>
      </CardHeader>
      <CardContent>
        {!capture.calendar_sync_valid && (
          <p className="desk-warning" role="alert">
            Tento draft vznikol bez úspešnej synchronizácie všetkých aktívnych kalendárov a nepočíta
            sa do akceptačných cyklov.
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
          <summary>Zobraziť zachytený draft</summary>
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
        <p className="shadow-hash">
          Kontrolný odtlačok <code>{capture.draft_sha256.slice(0, 16)}</code>
        </p>
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
  const uncertain = entry.messages.filter((message) => message.state === 'uncertain')
  return (
    <Card className="history-run" id={`run-${entry.id}`}>
      <CardHeader className="history-run-header">
        <div className={`history-state-icon ${successful ? 'success' : 'warning'}`}>
          {successful ? <CheckCircle2 /> : <AlertTriangle />}
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
          <summary>Zobraziť uložený obsah</summary>
          <div className="history-snapshot">
            {entry.intro_text && <p className="history-intro">{entry.intro_text}</p>}
            {entry.items.map((item) => (
              <article key={item.id}>
                <small>{item.display_time ?? kindLabel(item.kind)}</small>
                <strong>{item.title ?? 'Bez názvu'}</strong>
                {item.description && <p>{item.description}</p>}
              </article>
            ))}
            {entry.outro_text && <p>{entry.outro_text}</p>}
          </div>
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

  async function linkExisting() {
    if (!/^\d+$/.test(messageId)) {
      setError('Zadajte číselné ID správy z Discordu.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await linkExistingPublicationMessage(runId, position, messageId)
      onRecovered()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Obnova publikovania zlyhala.')
    } finally {
      setBusy(false)
    }
  }

  async function confirmNotSent() {
    setBusy(true)
    setError(null)
    try {
      await confirmPublicationMessageNotSent(runId, position)
      onRecovered()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Obnova publikovania zlyhala.')
    } finally {
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

function HistoryState({ text, retry }: { text: string; retry?: () => void }) {
  return (
    <div className="content-empty" role="status">
      <History />
      <strong>{text}</strong>
      {retry && <Button onClick={retry}>Skúsiť znova</Button>}
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
      sent: 'Odoslaná',
      pending: 'Čaká',
    }[value] ?? value.replaceAll('_', ' ')
  )
}

function kindLabel(value: string) {
  if (value === 'info') return 'INFO oznam'
  if (value === 'manual_event') return 'Manuálna udalosť'
  return 'Kalendárová udalosť'
}
