import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'

import {
  ApiError,
  deleteManualEvent,
  getManualEvents,
  type ManualEventRecord,
  saveManualEvent,
} from '../api/client'
import { ConfirmDialog, ContentDialog } from '../components/ContentDrawer'
import { useApiList } from '../hooks/useApiList'

export function ManualEventsPage() {
  const { items, loading, error, reload } = useApiList(getManualEvents)
  const [editing, setEditing] = useState<ManualEventRecord | 'new' | null>(null)
  const [deleting, setDeleting] = useState<ManualEventRecord | null>(null)
  const [deleteBusy, setDeleteBusy] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const active = items.filter((item) => !item.deleted_at)

  async function remove() {
    if (!deleting) return
    setDeleteBusy(true)
    try {
      await deleteManualEvent(deleting.id, deleting.version)
      await reload()
      setDeleting(null)
    } catch (caught) {
      setDeleteError(
        caught instanceof ApiError ? caught.message : 'Udalosť sa nepodarilo odstrániť.',
      )
    } finally {
      setDeleteBusy(false)
    }
  }

  return (
    <section className="content-page page-stack" aria-labelledby="manual-title">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Udalosti mimo Google kalendára</p>
          <h1 id="manual-title">Manuálne udalosti</h1>
          <p>Jednorazové položky, ktoré sa automaticky zaradia do správneho prehľadu.</p>
        </div>
        <button type="button" onClick={() => setEditing('new')}>
          Pridať udalosť
        </button>
      </header>

      {loading && <PageState text="Načítavam manuálne udalosti…" />}
      {error && <PageState text={error.message} retry={() => void reload()} />}
      {!loading && !error && active.length === 0 && (
        <div className="content-empty">
          <strong>Žiadne manuálne udalosti.</strong>
          <p>Všetko z Google kalendára sa pridáva automaticky. Tu patria iba výnimky.</p>
          <button type="button" onClick={() => setEditing('new')}>
            Pridať výnimku
          </button>
        </div>
      )}
      {!loading && !error && active.length > 0 && (
        <div className="record-list">
          {active.map((item) => (
            <article className="record-row" key={item.id}>
              <div className="record-date-block">
                <strong>{eventDate(item)}</strong>
                <span>{item.is_all_day ? 'Celodenná' : eventTime(item)}</span>
              </div>
              <div className="record-main">
                <div className="record-card-top">
                  <h2>{item.title}</h2>
                  <span className={`status-pill ${item.active ? 'status-ready' : 'status-muted'}`}>
                    {item.active ? 'Aktívna' : 'Pozastavená'}
                  </span>
                </div>
                {item.description && <p>{item.description}</p>}
              </div>
              <div className="record-actions record-row-actions">
                <button className="secondary-button" type="button" onClick={() => setEditing(item)}>
                  Upraviť
                </button>
                <button
                  className="quiet-danger"
                  type="button"
                  onClick={() => {
                    setDeleteError(null)
                    setDeleting(item)
                  }}
                >
                  Odstrániť
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      {editing && (
        <ManualEditor
          record={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            setEditing(null)
            await reload()
          }}
        />
      )}
      {deleting && (
        <ConfirmDialog
          title={`Odstrániť „${deleting.title}“?`}
          detail="Udalosť sa už nezaradí do budúcich oznamov. Zmena zostane dohľadateľná v audite."
          busy={deleteBusy}
          error={deleteError}
          onCancel={() => {
            setDeleteError(null)
            setDeleting(null)
          }}
          onConfirm={() => void remove()}
        />
      )}
    </section>
  )
}

export function ManualEditor({
  record,
  onClose,
  onSaved,
}: {
  record: ManualEventRecord | null
  onClose: () => void
  onSaved: () => Promise<void>
}) {
  const draftKey = `carlo:manual-event:${record?.id ?? 'new'}`
  const initial = useMemo(
    () => ({
      title: record?.title ?? '',
      description: record?.description ?? '',
      allDay: record?.is_all_day ?? false,
      startDate: record?.starts_on ?? localDate(record?.starts_at) ?? '',
      endDate: record?.ends_on ? addDays(record.ends_on, -1) : (localDate(record?.ends_at) ?? ''),
      startDateTime: localDateTime(record?.starts_at),
      endDateTime: localDateTime(record?.ends_at),
      linkUrl: record?.link_url ?? '',
      active: record?.active ?? true,
    }),
    [record],
  )
  const recovered = useMemo(() => readDraft<typeof initial>(draftKey), [draftKey])
  const [title, setTitle] = useState(recovered?.title ?? initial.title)
  const [description, setDescription] = useState(recovered?.description ?? initial.description)
  const [allDay, setAllDay] = useState(recovered?.allDay ?? initial.allDay)
  const [startDate, setStartDate] = useState(recovered?.startDate ?? initial.startDate)
  const [endDate, setEndDate] = useState(recovered?.endDate ?? initial.endDate)
  const [startDateTime, setStartDateTime] = useState(
    recovered?.startDateTime ?? initial.startDateTime,
  )
  const [endDateTime, setEndDateTime] = useState(recovered?.endDateTime ?? initial.endDateTime)
  const [linkUrl, setLinkUrl] = useState(recovered?.linkUrl ?? initial.linkUrl)
  const [active, setActive] = useState(recovered?.active ?? initial.active)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [expectedVersion, setExpectedVersion] = useState(record?.version)
  const [discarding, setDiscarding] = useState(false)
  const [versionNotice, setVersionNotice] = useState<string | null>(null)
  const saveInFlight = useRef(false)
  const values = useMemo(
    () => ({
      title,
      description,
      allDay,
      startDate,
      endDate,
      startDateTime,
      endDateTime,
      linkUrl,
      active,
    }),
    [active, allDay, description, endDate, endDateTime, linkUrl, startDate, startDateTime, title],
  )
  const dirty = JSON.stringify(values) !== JSON.stringify(initial)

  useEffect(() => {
    if (dirty) window.sessionStorage.setItem(draftKey, JSON.stringify(values))
    else window.sessionStorage.removeItem(draftKey)
  }, [dirty, draftKey, values])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (saveInFlight.current) return
    saveInFlight.current = true
    setBusy(true)
    setError(null)
    setVersionNotice(null)
    try {
      await saveManualEvent(
        {
          title: title.trim(),
          description: optional(description),
          is_all_day: allDay,
          starts_on: allDay ? startDate : null,
          ends_on: allDay && endDate ? addDays(endDate, 1) : null,
          starts_at: allDay ? null : bratislavaLocalToIso(startDateTime),
          ends_at: allDay ? null : optionalDateTime(endDateTime),
          timezone: 'Europe/Bratislava',
          link_url: optional(linkUrl),
          active,
          ...(expectedVersion ? { expected_version: expectedVersion } : {}),
        },
        record?.id,
      )
      window.sessionStorage.removeItem(draftKey)
      await onSaved()
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught
          : new ApiError('Udalosť sa nepodarilo uložiť.', 0, null),
      )
    } finally {
      saveInFlight.current = false
      setBusy(false)
    }
  }

  async function refreshVersion() {
    if (!record) return
    try {
      const latest = (await getManualEvents()).find((item) => item.id === record.id)
      if (!latest) {
        setVersionNotice('Udalosť už neexistuje. Rozpracované hodnoty zostali zachované.')
        return
      }
      setExpectedVersion(latest.version)
      setError(null)
      setVersionNotice(
        'Načítaná je novšia verzia záznamu. Vaše rozpracované hodnoty zostali zachované.',
      )
    } catch (caught) {
      setVersionNotice(
        caught instanceof ApiError ? caught.message : 'Novšiu verziu sa nepodarilo načítať.',
      )
    }
  }

  function requestClose() {
    if (dirty) setDiscarding(true)
    else onClose()
  }

  return (
    <ContentDialog
      eyebrow={record ? 'Úprava udalosti' : 'Nová manuálna udalosť'}
      title={record?.title ?? 'Pridať udalosť'}
      subtitle="Použite iba pre obsah, ktorý nie je v Google kalendári."
      busy={busy}
      onClose={requestClose}
    >
      <form className="drawer-form" onSubmit={submit}>
        <label className="form-field">
          <span>Názov</span>
          <input
            autoFocus
            required
            maxLength={256}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>
        <fieldset className="choice-section event-type-section">
          <legend>Typ udalosti</legend>
          <div className="segmented-control event-type-picker">
            <label>
              <input
                type="radio"
                name="event-type"
                checked={!allDay}
                onChange={() => setAllDay(false)}
              />
              <span>Udalosť s časom</span>
            </label>
            <label>
              <input
                type="radio"
                name="event-type"
                checked={allDay}
                onChange={() => setAllDay(true)}
              />
              <span>Celodenná udalosť</span>
            </label>
          </div>
          <p className="field-hint">
            Pri celodennej udalosti sa v ozname zobrazí iba deň alebo rozsah dní.
          </p>
        </fieldset>
        {allDay ? (
          <fieldset className="date-section">
            <legend>Termín udalosti</legend>
            <div className="date-grid">
              <label className="form-field date-field">
                <span>Prvý deň</span>
                <input
                  type="date"
                  required
                  value={startDate}
                  onChange={(event) => setStartDate(event.target.value)}
                />
              </label>
              <label className="form-field date-field">
                <span>Posledný deň</span>
                <input
                  type="date"
                  min={startDate}
                  value={endDate}
                  onChange={(event) => setEndDate(event.target.value)}
                />
              </label>
            </div>
            <p className="date-section-hint">
              Ak ide len o jeden deň, pole „Posledný deň“ nechajte prázdne.
            </p>
          </fieldset>
        ) : (
          <fieldset className="date-section">
            <legend>Termín a čas</legend>
            <div className="date-grid">
              <label className="form-field date-field">
                <span>Začína</span>
                <input
                  type="datetime-local"
                  required
                  value={startDateTime}
                  onChange={(event) => setStartDateTime(event.target.value)}
                />
              </label>
              <label className="form-field date-field">
                <span>Končí</span>
                <input
                  type="datetime-local"
                  min={startDateTime}
                  value={endDateTime}
                  onChange={(event) => setEndDateTime(event.target.value)}
                />
              </label>
            </div>
            <p className="date-section-hint">Koniec je voliteľný.</p>
          </fieldset>
        )}
        <label className="form-field">
          <span>Popis (voliteľný)</span>
          <textarea
            maxLength={4096}
            rows={6}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
          <small className="character-count">{description.length} / 4096</small>
        </label>
        <label className="form-field">
          <span>Odkaz (voliteľný)</span>
          <input
            type="url"
            placeholder="https://…"
            value={linkUrl}
            onChange={(event) => setLinkUrl(event.target.value)}
          />
        </label>
        <label className="switch-row">
          <span>
            <strong>Udalosť je aktívna</strong>
            <small>Neaktívna udalosť sa nebude publikovať.</small>
          </span>
          <input
            type="checkbox"
            checked={active}
            onChange={(event) => setActive(event.target.checked)}
          />
        </label>
        {error && (
          <div className="form-alert" role="alert">
            <strong>Udalosť sa nepodarilo uložiť</strong>
            <p>{error.message}</p>
            {error.status === 409 && (
              <button
                className="secondary-button alert-action"
                type="button"
                onClick={() => void refreshVersion()}
              >
                Načítať novšiu verziu a ponechať moje hodnoty
              </button>
            )}
          </div>
        )}
        {versionNotice && (
          <p className="form-notice" role="status">
            {versionNotice}
          </p>
        )}
        <footer className="drawer-actions">
          <button className="secondary-button" type="button" onClick={requestClose} disabled={busy}>
            Zrušiť
          </button>
          <button type="submit" disabled={busy}>
            {busy ? 'Ukladám…' : 'Uložiť udalosť'}
          </button>
        </footer>
      </form>
      {discarding && (
        <ConfirmDialog
          title="Zahodiť rozpracovanú udalosť?"
          detail="Neuložené hodnoty sa odstránia. Uložená udalosť zostane bez zmeny."
          busy={false}
          cancelLabel="Pokračovať v úprave"
          confirmLabel="Zahodiť zmeny"
          onCancel={() => setDiscarding(false)}
          onConfirm={() => {
            window.sessionStorage.removeItem(draftKey)
            setDiscarding(false)
            onClose()
          }}
        />
      )}
    </ContentDialog>
  )
}

function readDraft<T>(key: string): T | null {
  try {
    const value = window.sessionStorage.getItem(key)
    return value ? (JSON.parse(value) as T) : null
  } catch {
    return null
  }
}

function optional(value: string) {
  return value.trim() || null
}
function optionalDateTime(value: string) {
  return value ? bratislavaLocalToIso(value) : null
}

function addDays(value: string, count: number) {
  const date = new Date(`${value}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() + count)
  return date.toISOString().slice(0, 10)
}

function bratislavaLocalToIso(value: string) {
  const [datePart, timePart] = value.split('T')
  if (!datePart || !timePart) return value
  const [year = 0, month = 0, day = 0] = datePart.split('-').map(Number)
  const [hour = 0, minute = 0] = timePart.split(':').map(Number)
  const target = Date.UTC(year, month - 1, day, hour, minute)
  let instant = target
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Europe/Bratislava',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hourCycle: 'h23',
    }).formatToParts(new Date(instant))
    const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))
    const represented = Date.UTC(
      Number(values.year),
      Number(values.month) - 1,
      Number(values.day),
      Number(values.hour),
      Number(values.minute),
    )
    instant += target - represented
  }
  return new Date(instant).toISOString()
}

function localDateTime(value: string | null | undefined) {
  if (!value) return ''
  const parts = new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Europe/Bratislava',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date(value))
  const map = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${map.year}-${map.month}-${map.day}T${map.hour}:${map.minute}`
}

function localDate(value: string | null | undefined) {
  return localDateTime(value).slice(0, 10) || null
}
function eventDate(item: ManualEventRecord) {
  return item.starts_on
    ? formatAllDayRange(item.starts_on, item.ends_on)
    : item.starts_at
      ? new Intl.DateTimeFormat('sk-SK', { timeZone: item.timezone }).format(
          new Date(item.starts_at),
        )
      : 'Bez dátumu'
}

function formatAllDayRange(startsOn: string, endsOn: string | null) {
  const endInclusive = endsOn ? addDays(endsOn, -1) : startsOn
  const formatter = new Intl.DateTimeFormat('sk-SK', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
  const start = formatter.format(new Date(`${startsOn}T12:00:00`))
  if (endInclusive === startsOn) return start
  return `${start} – ${formatter.format(new Date(`${endInclusive}T12:00:00`))}`
}
function eventTime(item: ManualEventRecord) {
  return item.starts_at
    ? new Intl.DateTimeFormat('sk-SK', {
        timeZone: item.timezone,
        hour: '2-digit',
        minute: '2-digit',
      }).format(new Date(item.starts_at))
    : 'Bez času'
}
function PageState({ text, retry }: { text: string; retry?: () => void }) {
  return (
    <div className="content-empty" role="status">
      <strong>{text}</strong>
      {retry && <button onClick={retry}>Skúsiť znova</button>}
    </div>
  )
}
