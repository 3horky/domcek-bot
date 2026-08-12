import {
  AlertTriangle,
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
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  ApiError,
  cancelManualPublication,
  confirmManualPublication,
  getDashboardSummary,
  prepareManualPublication,
  releaseManualPublication,
  type DashboardSummary,
  type ManualPublicationPreview,
} from '../api/client'
import { useAuth } from '../auth/context'
import { DiscordPreview } from '../components/DiscordPreview'
import { EmptyState, LoadErrorState, LoadingState } from '../components/AsyncState'
import { Button } from '../components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog'
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
  const [summaryLoading, setSummaryLoading] = useState(true)
  const [summaryError, setSummaryError] = useState<string | null>(null)
  const [publishPreview, setPublishPreview] = useState<ManualPublicationPreview | null>(null)
  const [publishBusy, setPublishBusy] = useState(false)
  const [pendingPublication, setPendingPublication] = useState<{
    runId: string
    releaseAt: string
  } | null>(null)
  const [remainingSeconds, setRemainingSeconds] = useState(0)
  const [publishNotice, setPublishNotice] = useState<{
    kind: 'success' | 'error'
    text: string
  } | null>(null)
  const prepareInFlight = useRef(false)
  const confirmInFlight = useRef(false)
  const automaticReleaseStarted = useRef(false)
  const prepareButtonRef = useRef<HTMLButtonElement>(null)
  const canPublish =
    auth.status === 'authenticated' && auth.session.capabilities.includes('manual_publish')

  useEffect(() => {
    if (!pendingPublication) return
    const update = () => {
      setRemainingSeconds(
        Math.max(
          0,
          Math.ceil((new Date(pendingPublication.releaseAt).getTime() - Date.now()) / 1000),
        ),
      )
    }
    update()
    const timer = window.setInterval(update, 250)
    return () => window.clearInterval(timer)
  }, [pendingPublication])

  const loadSummary = useCallback(async (signal?: AbortSignal) => {
    setSummaryLoading(true)
    setSummaryError(null)
    try {
      setSummary(await getDashboardSummary(signal))
    } catch (caught) {
      if (signal?.aborted) return
      setSummaryError(
        caught instanceof ApiError ? caught.message : 'Prevádzkový stav sa nepodarilo načítať.',
      )
    } finally {
      if (!signal?.aborted) setSummaryLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!pendingPublication || remainingSeconds > 0 || automaticReleaseStarted.current) return
    automaticReleaseStarted.current = true
    const runId = pendingPublication.runId
    void releaseManualPublication(runId)
      .then(async (result) => {
        setPendingPublication(null)
        setPublishPreview(null)
        window.setTimeout(() => prepareButtonRef.current?.focus(), 180)
        setPublishNotice({
          kind: result.state.startsWith('succeeded') ? 'success' : 'error',
          text: result.state.startsWith('succeeded')
            ? 'Oznamy boli zverejnené. Najbližší pravidelný termín Carlo preskočí.'
            : 'Carlo nepotvrdil úspešné zverejnenie. Skontrolujte Históriu publikácií.',
        })
        await Promise.all([reload(), loadSummary()])
      })
      .catch((caught: unknown) => {
        setPublishNotice({
          kind: 'error',
          text: caught instanceof ApiError ? caught.message : 'Publikovanie sa nedokončilo.',
        })
      })
      .finally(() => {
        automaticReleaseStarted.current = false
      })
  }, [pendingPublication, remainingSeconds, loadSummary, reload])

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => void loadSummary(controller.signal), 0)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [loadSummary])

  if (loading) return <LoadingState label="Pripravujem prehľad…" />
  if (error) {
    return (
      <LoadErrorState
        title="Prehľad sa nepodarilo načítať"
        detail={error.message}
        onRetry={reload}
      />
    )
  }
  if (!draft)
    return (
      <EmptyState
        title="Najbližšie zverejnenie zatiaľ nie je dostupné"
        detail="Carlo ešte nemá z čoho zostaviť náhľad. Skúste údaje načítať znova."
        action={<Button onClick={reload}>Načítať znova</Button>}
      />
    )

  const eventCount = draft.public_items.filter((item) => item.kind !== 'info').length
  const infoCount = draft.public_items.filter((item) => item.kind === 'info').length
  const excludedCount = draft.editor_events.filter((item) => !item.included).length
  const calendarNeedsAttention =
    summary?.active_calendars.some(
      (calendar) => calendar.freshness !== 'fresh' || calendar.sync_status === 'failed',
    ) ?? false
  const needsAttention =
    draft.warnings.length > 0 ||
    calendarNeedsAttention ||
    summary?.automatic_publication_enabled === false ||
    Boolean(summaryError)
  const upcoming = draft.public_items.slice(0, 5)

  async function preparePublish() {
    if (prepareInFlight.current) return
    prepareInFlight.current = true
    setPublishBusy(true)
    setPublishNotice(null)
    try {
      setPublishPreview(await prepareManualPublication())
    } catch (caught) {
      setPublishNotice({
        kind: 'error',
        text:
          caught instanceof ApiError
            ? caught.message
            : 'Ručné zverejnenie sa nepodarilo pripraviť.',
      })
    } finally {
      prepareInFlight.current = false
      setPublishBusy(false)
    }
  }

  async function confirmPublish() {
    if (!publishPreview || confirmInFlight.current) return
    confirmInFlight.current = true
    setPublishBusy(true)
    setPublishNotice(null)
    try {
      const result = await confirmManualPublication(publishPreview.confirmation_token)
      if (result.state === 'waiting_for_release' && result.release_at) {
        setPendingPublication({ runId: result.run_id, releaseAt: result.release_at })
        setRemainingSeconds(1)
        setPublishNotice(null)
      } else if (result.state.startsWith('succeeded')) {
        closePublishPreview()
        setPublishNotice({
          kind: 'success',
          text: 'Oznamy boli zverejnené. Najbližší pravidelný termín Carlo preskočí.',
        })
        await Promise.all([reload(), loadSummary()])
      } else {
        setPublishNotice({
          kind: 'error',
          text: 'Carlo nepotvrdil úspešné zverejnenie. Skontrolujte Históriu publikácií.',
        })
      }
    } catch (caught) {
      setPublishNotice({
        kind: 'error',
        text:
          caught instanceof ApiError ? caught.message : 'Ručné zverejnenie sa nepodarilo dokončiť.',
      })
    } finally {
      confirmInFlight.current = false
      setPublishBusy(false)
    }
  }

  async function decideGuard(action: 'cancel' | 'release') {
    if (!pendingPublication || confirmInFlight.current) return
    confirmInFlight.current = true
    setPublishBusy(true)
    try {
      const result =
        action === 'cancel'
          ? await cancelManualPublication(pendingPublication.runId)
          : await releaseManualPublication(pendingPublication.runId)
      setPendingPublication(null)
      closePublishPreview()
      setPublishNotice({
        kind: result.state === 'cancelled' ? 'success' : 'success',
        text:
          result.state === 'cancelled'
            ? 'Publikovanie bolo zastavené. Na Discord sa nič neodoslalo.'
            : 'Oznamy boli zverejnené. Najbližší pravidelný termín Carlo preskočí.',
      })
      await Promise.all([reload(), loadSummary()])
    } catch (caught) {
      setPublishNotice({
        kind: 'error',
        text: caught instanceof ApiError ? caught.message : 'Rozhodnutie sa nepodarilo vykonať.',
      })
    } finally {
      confirmInFlight.current = false
      setPublishBusy(false)
    }
  }

  function closePublishPreview() {
    setPublishPreview(null)
    window.setTimeout(() => prepareButtonRef.current?.focus({ preventScroll: true }), 350)
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
            className={`status-pill ${needsAttention || summaryLoading ? 'status-warning' : 'status-ready'}`}
          >
            {summaryLoading
              ? 'Kontrolujem prevádzkový stav'
              : summaryError
                ? 'Prevádzkový stav treba overiť'
                : summary?.automatic_publication_enabled === false
                  ? 'Automatické publikovanie je pozastavené'
                  : calendarNeedsAttention || draft.warnings.length > 0
                    ? 'Treba skontrolovať'
                    : 'Pripravené na automatické zverejnenie'}
          </span>
          <p>Najbližšie zverejnenie</p>
          <h2>{publicationDate.format(new Date(draft.scheduled_for))}</h2>
          <small>Ak nič nezmeníte, Carlo oznamy zverejní automaticky v tomto termíne.</small>
        </div>
        <Link className="primary-button publication-action" to="/oznamy">
          Skontrolovať oznamy
          <ArrowRight aria-hidden="true" />
        </Link>
      </article>

      {summaryError && (
        <div className="dashboard-summary-warning" role="alert">
          <AlertTriangle aria-hidden="true" />
          <div>
            <strong>Prevádzkový stav nie je úplný</strong>
            <p>{summaryError} Obsah náhľadu zostal dostupný, no pred publikovaním stav overte.</p>
          </div>
          <Button variant="outline" onClick={() => void loadSummary()}>
            Skúsiť znova
          </Button>
        </div>
      )}

      {summary && !summary.last_publication && (
        <FirstRunGuide summary={summary} scheduledFor={draft.scheduled_for} />
      )}

      {canPublish && (
        <section className="dashboard-manual-publish" aria-labelledby="manual-publish-title">
          <div>
            <p className="eyebrow">Admin · SDB / FMA</p>
            <h2 id="manual-publish-title">Ručné zverejnenie</h2>
            <p>Vyžaduje dve potvrdenia. Úspech preskočí práve najbližší pravidelný termín.</p>
          </div>
          <Button
            ref={prepareButtonRef}
            type="button"
            disabled={publishBusy}
            onClick={() => void preparePublish()}
          >
            <Eye aria-hidden="true" />
            {publishBusy ? 'Pripravujem náhľad…' : 'Pripraviť náhľad na zverejnenie'}
          </Button>
          {publishNotice && (
            <p
              className={`dashboard-publish-notice ${publishNotice.kind}`}
              role={publishNotice.kind === 'error' ? 'alert' : 'status'}
            >
              {publishNotice.text}
            </p>
          )}
        </section>
      )}

      <Dialog
        open={publishPreview !== null}
        onOpenChange={(open) => {
          if (!open && !publishBusy) closePublishPreview()
        }}
      >
        <DialogContent
          className="dashboard-publish-dialog"
          finalFocus={() => prepareButtonRef.current}
          showCloseButton={!publishBusy}
        >
          <DialogHeader>
            <DialogTitle>Skontrolovať a ručne zverejniť</DialogTitle>
            <DialogDescription>
              Toto je presne obsah, ktorý Carlo po potvrdení odošle na Discord. Úspech preskočí
              najbližší pravidelný termín.
            </DialogDescription>
          </DialogHeader>
          {publishPreview && (
            <>
              <p className="dashboard-publish-counts">
                <strong>{publishPreview.announcement_count} položiek</strong> v{' '}
                {publishPreview.message_count}{' '}
                {publishPreview.message_count === 1 ? 'správe' : 'správach'}
              </p>
              <div className="dashboard-publish-preview">
                <DiscordPreview draft={publishPreview.draft} />
              </div>
            </>
          )}
          {pendingPublication && (
            <div className="publication-guard-countdown" role="status" aria-live="polite">
              <Clock3 aria-hidden="true" />
              <div>
                <strong>Carlo zatiaľ nič nezverejnil</strong>
                <span>
                  Automatické zverejnenie začne o {remainingSeconds}{' '}
                  {remainingSeconds === 1 ? 'sekundu' : 'sekúnd'}.
                </span>
              </div>
            </div>
          )}
          <DialogFooter>
            {pendingPublication ? (
              <>
                <Button
                  variant="outline"
                  type="button"
                  disabled={publishBusy || remainingSeconds <= 0}
                  onClick={() => void decideGuard('cancel')}
                >
                  <X aria-hidden="true" /> Zastaviť
                </Button>
                <Button
                  type="button"
                  disabled={publishBusy}
                  onClick={() => void decideGuard('release')}
                >
                  <Send aria-hidden="true" /> Zverejniť teraz
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="outline"
                  type="button"
                  disabled={publishBusy}
                  onClick={closePublishPreview}
                >
                  <X aria-hidden="true" /> Zrušiť
                </Button>
                <Button type="button" disabled={publishBusy} onClick={() => void confirmPublish()}>
                  <Send aria-hidden="true" />
                  {publishBusy ? 'Pripravujem…' : 'Potvrdiť publikovanie'}
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <section className="operational-strip" aria-label="Aktuálny prevádzkový stav">
        <OperationalItem
          icon={RefreshCw}
          label="Google kalendáre"
          value={calendarSummary(summary, summaryLoading, summaryError)}
          to="/nastavenia"
          attention={calendarNeedsAttention || Boolean(summaryError)}
        />
        <OperationalItem
          icon={History}
          label="Posledná publikácia"
          value={
            summary?.last_publication
              ? compactDate(
                  summary.last_publication.completed_at ?? summary.last_publication.scheduled_for,
                )
              : 'Ešte nepublikoval'
          }
          to="/historia"
        />
        <OperationalItem
          icon={Archive}
          label="Čakajúce archivácie"
          value={
            summaryLoading || summaryError
              ? 'Stav neznámy'
              : summary?.pending_archive_count
                ? `${summary.pending_archive_count}`
                : 'Žiadna'
          }
          to="/kanaly"
          attention={Boolean(summary?.pending_archive_count) || Boolean(summaryError)}
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
  attention = false,
}: {
  icon: typeof RefreshCw
  label: string
  value: string
  to?: string
  attention?: boolean
}) {
  const content = (
    <>
      <Icon className={attention ? 'attention' : undefined} aria-hidden="true" />
      <span>
        <small>{label}</small>
        <strong>{value}</strong>
      </span>
    </>
  )
  return to ? <Link to={to}>{content}</Link> : <div>{content}</div>
}

function FirstRunGuide({
  summary,
  scheduledFor,
}: {
  summary: DashboardSummary
  scheduledFor: string
}) {
  return (
    <section className="first-run-guide" aria-labelledby="first-run-title">
      <header>
        <div>
          <p className="eyebrow">Prvé spustenie</p>
          <h2 id="first-run-title">Dokončite základné nastavenie Carla</h2>
          <p>Kalendár je voliteľný. Oznamy môžete pripraviť aj iba z ručne pridaného obsahu.</p>
        </div>
        <span>
          {summary.discord_places_configured ? 'Základ je pripravený' : 'Začnite miestami'}
        </span>
      </header>
      <ol>
        <li className={summary.discord_places_configured ? 'complete' : 'current'}>
          <CheckCircle2 aria-hidden="true" />
          <div>
            <strong>Miesta na Discorde</strong>
            <small>
              {summary.discord_places_configured
                ? 'Kanál pre oznamy je vybraný.'
                : 'Vyberte, kam má Carlo oznamy posielať.'}
            </small>
          </div>
          <Link to="/nastavenia">
            {summary.discord_places_configured ? 'Skontrolovať' : 'Nastaviť'}
          </Link>
        </li>
        <li className={summary.active_calendars.length > 0 ? 'complete' : ''}>
          <CalendarDays aria-hidden="true" />
          <div>
            <strong>Google kalendár</strong>
            <small>
              {summary.active_calendars.length > 0
                ? `${summary.active_calendars.length} aktívnych zdrojov.`
                : 'Voliteľné — Carlo funguje aj bez kalendára.'}
            </small>
          </div>
          <Link to="/nastavenia">
            {summary.active_calendars.length > 0 ? 'Skontrolovať' : 'Pridať'}
          </Link>
        </li>
        <li className="complete">
          <Clock3 aria-hidden="true" />
          <div>
            <strong>Harmonogram</strong>
            <small>Najbližšie zverejnenie {publicationDate.format(new Date(scheduledFor))}.</small>
          </div>
          <Link to="/nastavenia">Upraviť</Link>
        </li>
        <li className="current">
          <Eye aria-hidden="true" />
          <div>
            <strong>Skontrolovať výsledok</strong>
            <small>Otvorte kanonický Discord náhľad pred prvým zverejnením.</small>
          </div>
          <Link to="/oznamy">Otvoriť náhľad</Link>
        </li>
      </ol>
    </section>
  )
}

function calendarSummary(summary: DashboardSummary | null, loading: boolean, error: string | null) {
  if (loading) return 'Kontrolujem stav…'
  if (error || !summary) return 'Stav neznámy'
  if (summary.active_calendars.length === 0) return 'Funguje bez kalendára'
  const attention = summary.active_calendars.filter(
    (calendar) => calendar.freshness !== 'fresh' || calendar.sync_status === 'failed',
  ).length
  if (attention > 0) return `${attention} z ${summary.active_calendars.length} vyžaduje pozornosť`
  return `${summary.active_calendars.length} z ${summary.active_calendars.length} pripravené`
}

function compactDate(value: string) {
  return new Intl.DateTimeFormat('sk-SK', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Europe/Bratislava',
  }).format(new Date(value))
}
