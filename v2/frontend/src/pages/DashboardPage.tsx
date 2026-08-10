import {
  Archive,
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Eye,
  History,
  Info,
  RefreshCw,
  Send,
  X,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  ApiError,
  confirmManualPublication,
  getDashboardSummary,
  prepareManualPublication,
  type DashboardSummary,
  type ManualPublicationPreview,
} from '../api/client'
import { useAuth } from '../auth/context'
import { usePublicationDraft } from '../hooks/usePublicationDraft'

const publicationDate = new Intl.DateTimeFormat('sk-SK', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  hour: '2-digit',
  minute: '2-digit',
})

const shortDate = new Intl.DateTimeFormat('sk-SK', {
  day: 'numeric',
  month: 'long',
})

export function DashboardPage() {
  const auth = useAuth()
  const { draft, error, loading, reload } = usePublicationDraft()
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [publishPreview, setPublishPreview] = useState<ManualPublicationPreview | null>(null)
  const [publishBusy, setPublishBusy] = useState(false)
  const [publishNotice, setPublishNotice] = useState<string | null>(null)
  const canPublish =
    auth.status === 'authenticated' && auth.session.capabilities.includes('manual_publish')

  useEffect(() => {
    const controller = new AbortController()
    void getDashboardSummary(controller.signal)
      .then(setSummary)
      .catch(() => setSummary(null))
    return () => controller.abort()
  }, [])

  if (loading) return <PageState title="Pripravujem prehľad…" />
  if (error) {
    return <PageState title="Prehľad sa nepodarilo načítať" detail={error.message} retry={reload} />
  }
  if (!draft)
    return <PageState title="Najbližšie zverejnenie zatiaľ nie je dostupné" retry={reload} />

  const eventCount = draft.public_items.filter((item) => item.kind !== 'info').length
  const infoCount = draft.public_items.filter((item) => item.kind === 'info').length
  const excludedCount = draft.editor_events.filter((item) => !item.included).length
  const needsAttention = draft.warnings.length > 0
  const upcoming = draft.public_items.slice(0, 5)

  async function preparePublish() {
    setPublishBusy(true)
    setPublishNotice(null)
    try {
      setPublishPreview(await prepareManualPublication())
    } catch (caught) {
      setPublishNotice(
        caught instanceof ApiError ? caught.message : 'Ručné zverejnenie sa nepodarilo pripraviť.',
      )
    } finally {
      setPublishBusy(false)
    }
  }

  async function confirmPublish() {
    if (!publishPreview) return
    setPublishBusy(true)
    setPublishNotice(null)
    try {
      const result = await confirmManualPublication(publishPreview.confirmation_token)
      setPublishPreview(null)
      setPublishNotice(`Publikovanie skončilo stavom ${result.state}.`)
    } catch (caught) {
      setPublishNotice(
        caught instanceof ApiError ? caught.message : 'Ručné zverejnenie sa nepodarilo dokončiť.',
      )
    } finally {
      setPublishBusy(false)
    }
  }

  return (
    <section className="dashboard-page" aria-labelledby="page-title">
      <header className="dashboard-title">
        <div>
          <p className="eyebrow">Carlo</p>
          <h1 id="page-title">Prehľad</h1>
          <p>Všetko podstatné o najbližšom automatickom zverejnení.</p>
        </div>
      </header>

      <article className="next-publication-card">
        <div className="publication-status-icon" aria-hidden="true">
          {needsAttention ? <Eye /> : <CheckCircle2 />}
        </div>
        <div className="next-publication-copy">
          <span
            className={`status-pill ${needsAttention || summary?.automatic_publication_enabled === false ? 'status-warning' : 'status-ready'}`}
          >
            {summary?.automatic_publication_enabled === false
              ? 'Automatické publikovanie je pozastavené'
              : needsAttention
                ? 'Treba skontrolovať'
                : 'Pripravené na automatické zverejnenie'}
          </span>
          <p>Najbližšie zverejnenie</p>
          <h2>{publicationDate.format(new Date(draft.scheduled_for))}</h2>
          <small>Ak nič nezmeníš, Carlo oznamy zverejní automaticky v tomto termíne.</small>
        </div>
        <Link className="primary-button publication-action" to="/oznamy">
          Skontrolovať oznamy
          <ArrowRight aria-hidden="true" />
        </Link>
      </article>

      {canPublish && (
        <section className="dashboard-manual-publish" aria-labelledby="manual-publish-title">
          <div>
            <p className="eyebrow">Admin · SDB / FMA</p>
            <h2 id="manual-publish-title">Ručné zverejnenie</h2>
            <p>Vyžaduje dve potvrdenia. Úspech preskočí práve najbližší pravidelný termín.</p>
          </div>
          {publishPreview ? (
            <div className="dashboard-publish-confirm">
              <p>
                <strong>{publishPreview.announcement_count} položiek</strong> ·{' '}
                {publishPreview.message_count} správ
              </p>
              <button
                className="secondary-button"
                type="button"
                disabled={publishBusy}
                onClick={() => setPublishPreview(null)}
              >
                <X aria-hidden="true" /> Zrušiť
              </button>
              <button type="button" disabled={publishBusy} onClick={() => void confirmPublish()}>
                <Send aria-hidden="true" />
                {publishBusy ? 'Publikujem…' : 'Potvrdiť a zverejniť'}
              </button>
            </div>
          ) : (
            <button type="button" disabled={publishBusy} onClick={() => void preparePublish()}>
              <Send aria-hidden="true" />
              {publishBusy ? 'Pripravujem…' : 'Pripraviť ručné zverejnenie'}
            </button>
          )}
          {publishNotice && (
            <p className="dashboard-publish-notice" role="status">
              {publishNotice}
            </p>
          )}
        </section>
      )}

      <section className="operational-strip" aria-label="Aktuálny prevádzkový stav">
        <OperationalItem
          icon={RefreshCw}
          label="Posledná synchronizácia"
          value={
            summary?.last_calendar_sync_at
              ? compactDate(summary.last_calendar_sync_at)
              : 'Zatiaľ bez syncu'
          }
        />
        <OperationalItem
          icon={History}
          label="Posledná publikácia"
          value={
            summary?.last_publication
              ? compactDate(
                  summary.last_publication.completed_at ?? summary.last_publication.scheduled_for,
                )
              : 'Zatiaľ bez publikácie'
          }
          to="/historia"
        />
        <OperationalItem
          icon={Archive}
          label="Čakajúce archivácie"
          value={`${summary?.pending_archive_count ?? 0}`}
          to="/nastavenia"
        />
      </section>

      <div className="dashboard-content-grid">
        <section className="dashboard-panel" aria-labelledby="package-title">
          <header className="dashboard-panel-header">
            <div>
              <p className="eyebrow">Čo sa zverejní</p>
              <h2 id="package-title">Obsah najbližšieho prehľadu</h2>
            </div>
            <span className="package-total">{draft.public_items.length} položiek</span>
          </header>

          <div className="package-summary">
            <div>
              <CalendarDays aria-hidden="true" />
              <strong>{eventCount}</strong>
              <span>{eventCount === 1 ? 'udalosť' : 'udalostí'}</span>
            </div>
            <div>
              <Info aria-hidden="true" />
              <strong>{infoCount}</strong>
              <span>INFO oznamov</span>
            </div>
          </div>

          {upcoming.length > 0 ? (
            <div className="upcoming-list">
              {upcoming.map((item) => (
                <div className="upcoming-item" key={`${item.kind}-${item.source_id}`}>
                  <span className="upcoming-marker" aria-hidden="true" />
                  <div>
                    <strong>{item.title}</strong>
                    <small>
                      {item.display_time ?? (item.kind === 'info' ? 'INFO oznam' : 'Bez času')}
                    </small>
                  </div>
                </div>
              ))}
              {draft.public_items.length > upcoming.length && (
                <p className="remaining-items">
                  a ďalších {draft.public_items.length - upcoming.length} položiek
                </p>
              )}
            </div>
          ) : (
            <p className="dashboard-empty-copy">
              V najbližšom prehľade zatiaľ nie je žiadny obsah.
            </p>
          )}
        </section>

        <aside className="dashboard-side-stack" aria-label="Podrobnosti zverejnenia">
          <section className="dashboard-panel compact-panel">
            <div className="panel-icon" aria-hidden="true">
              <Clock3 />
            </div>
            <div>
              <p className="eyebrow">Obdobie oznamov</p>
              <h2>
                {shortDate.format(new Date(draft.window_starts_at))} –{' '}
                {shortDate.format(new Date(draft.window_ends_at))}
              </h2>
              <p>Udalosti, ktoré sa konajú počas najbližších dvoch týždňov.</p>
            </div>
          </section>

          <section className={`review-card${needsAttention ? ' needs-attention' : ''}`}>
            <p className="eyebrow">Kontrola obsahu</p>
            <h2>{needsAttention ? 'Preview obsahuje upozornenia' : 'Všetko vyzerá v poriadku'}</h2>
            <p>
              {needsAttention
                ? `${draft.warnings.length} upozornení si pred zverejnením vyžaduje kontrolu.`
                : excludedCount > 0
                  ? `${excludedCount} udalostí je zámerne vynechaných. Ostatný obsah je pripravený.`
                  : 'Nie je potrebný žiadny zásah. Redakčná úprava zostáva dobrovoľná.'}
            </p>
            <Link to="/oznamy">Pozrieť celý obsah</Link>
          </section>
        </aside>
      </div>
    </section>
  )
}

function OperationalItem({
  icon: Icon,
  label,
  value,
  to,
}: {
  icon: typeof RefreshCw
  label: string
  value: string
  to?: string
}) {
  const content = (
    <>
      <Icon aria-hidden="true" />
      <span>
        <small>{label}</small>
        <strong>{value}</strong>
      </span>
    </>
  )
  return to ? <Link to={to}>{content}</Link> : <div>{content}</div>
}

function compactDate(value: string) {
  return new Intl.DateTimeFormat('sk-SK', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Europe/Bratislava',
  }).format(new Date(value))
}

function PageState({
  title,
  detail,
  retry,
}: {
  title: string
  detail?: string
  retry?: () => void
}) {
  return (
    <section className="content-state" aria-live="polite">
      <span className="loading-orb" aria-hidden="true" />
      <h1>{title}</h1>
      {detail && <p>{detail}</p>}
      {retry && <button onClick={retry}>Skúsiť znova</button>}
    </section>
  )
}
