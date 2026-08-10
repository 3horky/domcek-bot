import { useMemo, useState } from 'react'
import {
  CalendarDays,
  CalendarPlus,
  CircleSlash2,
  Info,
  Layers3,
  PenLine,
  Plus,
  RefreshCw,
  Trash2,
} from 'lucide-react'

import {
  ApiError,
  deleteInfoAnnouncement,
  deleteManualEvent,
  getInfoAnnouncements,
  getManualEvents,
  type DraftItem,
  type InfoAnnouncementRecord,
  type ManualEventRecord,
} from '../api/client'
import { useAuth } from '../auth/context'
import { ConfirmDialog } from '../components/ContentDrawer'
import { DiscordPreview } from '../components/DiscordPreview'
import { EventEditorPanel } from '../components/EventEditorPanel'
import { useApiList } from '../hooks/useApiList'
import { usePublicationDraft } from '../hooks/usePublicationDraft'
import { InfoEditor } from './InfoAnnouncementsPage'
import { ManualEditor } from './ManualEventsPage'

type DeskFilter = 'publication' | 'calendar' | 'manual' | 'info' | 'excluded'

interface WorkspaceEntry {
  key: string
  kind: DraftItem['kind']
  title: string
  description: string | null
  schedule: string
  included: boolean
  calendar?: DraftItem
  manual?: ManualEventRecord
  info?: InfoAnnouncementRecord
}

type DeleteTarget =
  { kind: 'manual'; record: ManualEventRecord } | { kind: 'info'; record: InfoAnnouncementRecord }

const publicationDate = new Intl.DateTimeFormat('sk-SK', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  hour: '2-digit',
  minute: '2-digit',
})

const emptyManualEvents = async () => [] as ManualEventRecord[]
const emptyInfoAnnouncements = async () => [] as InfoAnnouncementRecord[]

export function AnnouncementsPage() {
  const { draft, error, loading, reload } = usePublicationDraft()
  const auth = useAuth()
  const capabilities = auth.status === 'authenticated' ? auth.session.capabilities : []
  const canEdit = capabilities.includes('edit_content')
  const canForceInclusion = capabilities.includes('force_inclusion')
  const manual = useApiList(canEdit ? getManualEvents : emptyManualEvents)
  const info = useApiList(canEdit ? getInfoAnnouncements : emptyInfoAnnouncements)
  const [filter, setFilter] = useState<DeskFilter>('publication')
  const [selectedCalendar, setSelectedCalendar] = useState<DraftItem | null>(null)
  const [editingManual, setEditingManual] = useState<ManualEventRecord | 'new' | null>(null)
  const [editingInfo, setEditingInfo] = useState<InfoAnnouncementRecord | 'new' | null>(null)
  const [deleting, setDeleting] = useState<DeleteTarget | null>(null)
  const [deleteBusy, setDeleteBusy] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [savedNotice, setSavedNotice] = useState(false)

  const activeManual = useMemo(
    () => manual.items.filter((item) => !item.deleted_at),
    [manual.items],
  )
  const activeInfo = useMemo(() => info.items.filter((item) => !item.deleted_at), [info.items])

  const entries = useMemo(() => {
    if (!draft) return []
    const publication = draft.public_items.map((item) =>
      entryFromDraft(
        item,
        activeManual.find((record) => record.id === item.source_id),
        activeInfo.find((record) => record.id === item.source_id),
      ),
    )
    if (filter === 'publication') return publication
    if (filter === 'calendar') return draft.editor_events.map((item) => entryFromDraft(item))
    if (filter === 'excluded') {
      return draft.editor_events
        .filter((item) => !item.included)
        .map((item) => entryFromDraft(item))
    }
    if (filter === 'manual') {
      return activeManual.map((record) =>
        entryFromManual(
          record,
          draft.public_items.find(
            (item) => item.kind === 'manual_event' && item.source_id === record.id,
          ),
        ),
      )
    }
    return activeInfo.map((record) =>
      entryFromInfo(
        record,
        draft.public_items.find((item) => item.kind === 'info' && item.source_id === record.id),
      ),
    )
  }, [activeInfo, activeManual, draft, filter])

  async function reloadAll() {
    await Promise.all([reload(), ...(canEdit ? [manual.reload(), info.reload()] : [])])
  }

  async function handleSaved() {
    await reloadAll()
    setSelectedCalendar(null)
    setEditingManual(null)
    setEditingInfo(null)
    setSavedNotice(true)
    window.setTimeout(() => setSavedNotice(false), 4000)
  }

  async function remove() {
    if (!deleting) return
    setDeleteBusy(true)
    setDeleteError(null)
    try {
      if (deleting.kind === 'manual') {
        await deleteManualEvent(deleting.record.id, deleting.record.version)
      } else {
        await deleteInfoAnnouncement(deleting.record.id, deleting.record.version)
      }
      setDeleting(null)
      await reloadAll()
    } catch (caught) {
      setDeleteError(
        caught instanceof ApiError ? caught.message : 'Položku sa nepodarilo odstrániť.',
      )
    } finally {
      setDeleteBusy(false)
    }
  }

  if (loading) return <EditorState title="Carlo pripravuje redakčný pult…" />
  if (error) {
    return <EditorState title="Obsah sa nepodarilo načítať" detail={error.message} retry={reload} />
  }
  if (!draft) return <EditorState title="Najbližší prehľad zatiaľ nie je dostupný" retry={reload} />

  const excludedCount = draft.editor_events.filter((item) => !item.included).length
  const filterItems: Array<{
    key: DeskFilter
    label: string
    count: number
    icon: typeof Layers3
  }> = [
    {
      key: 'publication',
      label: 'Najbližší prehľad',
      count: draft.public_items.length,
      icon: Layers3,
    },
    {
      key: 'calendar',
      label: 'Google kalendár',
      count: draft.editor_events.length,
      icon: CalendarDays,
    },
    { key: 'manual', label: 'Manuálne', count: activeManual.length, icon: PenLine },
    { key: 'info', label: 'INFO', count: activeInfo.length, icon: Info },
    { key: 'excluded', label: 'Nezverejnia sa', count: excludedCount, icon: CircleSlash2 },
  ]

  return (
    <section className="editorial-desk" aria-labelledby="page-title">
      <header className="desk-toolbar">
        <div>
          <p className="eyebrow">Najbližšie automatické zverejnenie</p>
          <h1 id="page-title">Redakčný pult</h1>
          <p>
            Carlo zverejní prehľad {publicationDate.format(new Date(draft.scheduled_for))}. Všetky
            tri zdroje obsahu spravuješ tu.
          </p>
        </div>
        <button
          className="secondary-button refresh-content-button"
          onClick={() => void reloadAll()}
        >
          <RefreshCw aria-hidden="true" />
          Načítať aktuálne údaje
        </button>
      </header>

      {(manual.error || info.error) && canEdit && (
        <div className="desk-warning" role="alert">
          Vlastný obsah sa nepodarilo úplne načítať. Skús načítať aktuálne údaje znova.
        </div>
      )}

      <div className="desk-shell">
        <aside className="desk-rail" aria-label="Zdroje obsahu">
          <div className="desk-filter-list">
            <p className="desk-section-label">Zobraziť</p>
            {filterItems.map((item) => (
              <button
                key={item.key}
                className={filter === item.key ? 'active' : ''}
                type="button"
                aria-pressed={filter === item.key}
                onClick={() => setFilter(item.key)}
              >
                <item.icon aria-hidden="true" />
                <span>{item.label}</span>
                <strong>{item.count}</strong>
              </button>
            ))}
          </div>
          {canEdit && (
            <div className="desk-create-actions">
              <p className="desk-section-label">Pridať obsah</p>
              <button type="button" onClick={() => setEditingManual('new')}>
                <CalendarPlus aria-hidden="true" />
                Manuálnu udalosť
              </button>
              <button type="button" onClick={() => setEditingInfo('new')}>
                <Plus aria-hidden="true" />
                INFO oznam
              </button>
            </div>
          )}
        </aside>

        <section className="desk-content" aria-labelledby="desk-list-title">
          <header className="desk-panel-header">
            <div>
              <p className="eyebrow">{filterTitle(filter).eyebrow}</p>
              <h2 id="desk-list-title">{filterTitle(filter).title}</h2>
            </div>
            <span>
              {entries.length} {entries.length === 1 ? 'položka' : 'položiek'}
            </span>
          </header>
          <div className="desk-entry-list">
            {entries.length === 0 ? (
              <DeskEmpty
                filter={filter}
                canEdit={canEdit}
                onAddManual={() => setEditingManual('new')}
                onAddInfo={() => setEditingInfo('new')}
              />
            ) : (
              entries.map((entry) => (
                <ContentEntry
                  key={entry.key}
                  entry={entry}
                  canEdit={canEdit}
                  onEdit={() => {
                    if (entry.calendar) setSelectedCalendar(entry.calendar)
                    else if (entry.manual) setEditingManual(entry.manual)
                    else if (entry.info) setEditingInfo(entry.info)
                  }}
                  onDelete={
                    entry.manual
                      ? () => setDeleting({ kind: 'manual', record: entry.manual! })
                      : entry.info
                        ? () => setDeleting({ kind: 'info', record: entry.info! })
                        : undefined
                  }
                />
              ))
            )}
          </div>
        </section>

        <aside className="desk-preview" aria-labelledby="discord-preview-title">
          <header className="desk-panel-header">
            <div>
              <p className="eyebrow">Výsledok</p>
              <h2 id="discord-preview-title">Discord náhľad</h2>
            </div>
            <span>
              {draft.messages.length} {draft.messages.length === 1 ? 'správa' : 'správy'}
            </span>
          </header>
          <DiscordPreview draft={draft} />
        </aside>
      </div>

      {selectedCalendar && (
        <EventEditorPanel
          item={selectedCalendar}
          canForceInclusion={canForceInclusion}
          onClose={() => setSelectedCalendar(null)}
          onSaved={handleSaved}
          onConflictReload={async () => {
            await reloadAll()
            setSelectedCalendar(null)
          }}
        />
      )}
      {editingManual && (
        <ManualEditor
          record={editingManual === 'new' ? null : editingManual}
          onClose={() => setEditingManual(null)}
          onSaved={handleSaved}
        />
      )}
      {editingInfo && (
        <InfoEditor
          record={editingInfo === 'new' ? null : editingInfo}
          onClose={() => setEditingInfo(null)}
          onSaved={handleSaved}
        />
      )}
      {deleting && (
        <ConfirmDialog
          title={`Odstrániť „${deleting.record.title}“?`}
          detail="Položka sa prestane zaraďovať do budúcich oznamov. Zmena zostane dohľadateľná v audite."
          busy={deleteBusy}
          error={deleteError}
          onCancel={() => {
            setDeleteError(null)
            setDeleting(null)
          }}
          onConfirm={() => void remove()}
        />
      )}
      {savedNotice && (
        <div className="toast" role="status">
          <span aria-hidden="true">✓</span>
          Zmena je uložená a Discord náhľad je aktuálny.
        </div>
      )}
    </section>
  )
}

function ContentEntry({
  entry,
  canEdit,
  onEdit,
  onDelete,
}: {
  entry: WorkspaceEntry
  canEdit: boolean
  onEdit: () => void
  onDelete?: () => void
}) {
  const Icon =
    entry.kind === 'external_event' ? CalendarDays : entry.kind === 'manual_event' ? PenLine : Info
  const source =
    entry.kind === 'external_event'
      ? 'Google kalendár'
      : entry.kind === 'manual_event'
        ? 'Manuálna udalosť'
        : 'INFO oznam'
  const editable =
    canEdit && (entry.kind === 'external_event' || Boolean(entry.manual || entry.info))

  return (
    <article
      className={`desk-entry${entry.included ? '' : ' is-outside'}${editable ? ' is-editable' : ''}`}
    >
      <button
        className="desk-entry-open"
        type="button"
        disabled={!editable}
        onClick={onEdit}
        aria-label={`Upraviť ${entry.title}`}
      >
        <div className={`desk-entry-icon kind-${entry.kind}`} aria-hidden="true">
          <Icon />
        </div>
        <div className="desk-entry-copy">
          <div className="desk-entry-meta">
            <span>{source}</span>
            <span aria-hidden="true">·</span>
            <span>{entry.schedule}</span>
          </div>
          <h3>{entry.title}</h3>
          {entry.description && <p>{entry.description}</p>}
          <span className={`desk-entry-state${entry.included ? ' included' : ''}`}>
            {entry.included
              ? 'V najbližšom prehľade'
              : entry.calendar
                ? 'Nezverejní sa'
                : 'Mimo najbližšieho prehľadu'}
          </span>
        </div>
      </button>
      <div className="desk-entry-actions">
        <button type="button" disabled={!editable} onClick={onEdit}>
          Upraviť
        </button>
        {onDelete && (
          <button
            className="delete-entry"
            type="button"
            onClick={onDelete}
            aria-label={`Odstrániť ${entry.title}`}
          >
            <Trash2 aria-hidden="true" />
          </button>
        )}
      </div>
    </article>
  )
}

function DeskEmpty({
  filter,
  canEdit,
  onAddManual,
  onAddInfo,
}: {
  filter: DeskFilter
  canEdit: boolean
  onAddManual: () => void
  onAddInfo: () => void
}) {
  const copy: Record<DeskFilter, { title: string; detail: string }> = {
    publication: {
      title: 'Najbližší prehľad je zatiaľ prázdny',
      detail: 'Kalendárové, manuálne aj INFO položky sa tu zobrazia spolu.',
    },
    calendar: {
      title: 'V tomto období nie sú udalosti z Google kalendára',
      detail: 'Manuálne udalosti a INFO oznamy môžu byť napriek tomu súčasťou prehľadu.',
    },
    manual: {
      title: 'Nie sú vytvorené manuálne udalosti',
      detail: 'Používajú sa iba pre obsah mimo Google kalendára.',
    },
    info: {
      title: 'Nie sú vytvorené INFO oznamy',
      detail: 'INFO oznam má vlastnú platnosť a voliteľný obrázok.',
    },
    excluded: {
      title: 'Žiadne udalosti nie sú vylúčené',
      detail: 'Všetky kalendárové udalosti sa spracujú automaticky.',
    },
  }
  return (
    <div className="desk-empty">
      <strong>{copy[filter].title}</strong>
      <p>{copy[filter].detail}</p>
      {canEdit && filter === 'manual' && (
        <button onClick={onAddManual}>Pridať manuálnu udalosť</button>
      )}
      {canEdit && filter === 'info' && <button onClick={onAddInfo}>Pridať INFO oznam</button>}
    </div>
  )
}

function entryFromDraft(
  item: DraftItem,
  manual?: ManualEventRecord,
  info?: InfoAnnouncementRecord,
): WorkspaceEntry {
  return {
    key: `${item.kind}-${item.source_id}`,
    kind: item.kind,
    title: item.title,
    description: item.description,
    schedule:
      item.display_time ?? (item.kind === 'info' ? 'Platný INFO oznam' : 'Bez uvedeného času'),
    included: item.included,
    calendar: item.kind === 'external_event' ? item : undefined,
    manual,
    info,
  }
}

function entryFromManual(record: ManualEventRecord, draftItem?: DraftItem): WorkspaceEntry {
  return {
    key: `manual_event-${record.id}`,
    kind: 'manual_event',
    title: record.title,
    description: record.description,
    schedule: manualSchedule(record),
    included: Boolean(draftItem),
    manual: record,
  }
}

function entryFromInfo(record: InfoAnnouncementRecord, draftItem?: DraftItem): WorkspaceEntry {
  return {
    key: `info-${record.id}`,
    kind: 'info',
    title: record.title,
    description: record.description,
    schedule: `Platí ${formatDate(record.valid_from)} – ${formatDate(record.valid_until)}`,
    included: Boolean(draftItem),
    info: record,
  }
}

function manualSchedule(record: ManualEventRecord) {
  if (record.starts_on) {
    const inclusiveEnd = record.ends_on ? addDays(record.ends_on, -1) : record.starts_on
    if (inclusiveEnd === record.starts_on) return `Celý deň · ${formatDate(record.starts_on)}`
    return `Celodenná · ${formatDate(record.starts_on)} – ${formatDate(inclusiveEnd)}`
  }
  if (!record.starts_at) return 'Bez uvedeného termínu'
  return new Intl.DateTimeFormat('sk-SK', {
    timeZone: record.timezone,
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(record.starts_at))
}

function addDays(value: string, count: number) {
  const date = new Date(`${value}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() + count)
  return date.toISOString().slice(0, 10)
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('sk-SK', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(`${value}T12:00:00`))
}

function filterTitle(filter: DeskFilter) {
  const values: Record<DeskFilter, { eyebrow: string; title: string }> = {
    publication: { eyebrow: 'Spoločný výsledok', title: 'Obsah najbližšieho prehľadu' },
    calendar: { eyebrow: 'Automatický zdroj', title: 'Udalosti z Google kalendára' },
    manual: { eyebrow: 'Vlastný obsah', title: 'Manuálne udalosti' },
    info: { eyebrow: 'Vlastný obsah', title: 'INFO oznamy' },
    excluded: { eyebrow: 'Kontrola', title: 'Položky, ktoré sa nezverejnia' },
  }
  return values[filter]
}

function EditorState({
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
      <h1>{title}</h1>
      {detail && <p>{detail}</p>}
      {retry && <button onClick={retry}>Skúsiť znova</button>}
    </section>
  )
}
