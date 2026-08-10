import { useState, type FormEvent } from 'react'
import { ImagePlus, UploadCloud, X } from 'lucide-react'

import {
  ApiError,
  deleteInfoAnnouncement,
  getInfoAnnouncements,
  type InfoAnnouncementRecord,
  saveInfoAnnouncement,
  uploadInfoImage,
} from '../api/client'
import { ConfirmDialog, ContentDialog } from '../components/ContentDrawer'
import { useApiList } from '../hooks/useApiList'

export function InfoAnnouncementsPage() {
  const { items, loading, error, reload } = useApiList(getInfoAnnouncements)
  const [editing, setEditing] = useState<InfoAnnouncementRecord | 'new' | null>(null)
  const [deleting, setDeleting] = useState<InfoAnnouncementRecord | null>(null)
  const [deleteBusy, setDeleteBusy] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const active = items.filter((item) => !item.deleted_at)

  async function remove() {
    if (!deleting) return
    setDeleteBusy(true)
    try {
      await deleteInfoAnnouncement(deleting.id, deleting.version)
      await reload()
      setDeleting(null)
    } catch (caught) {
      setDeleteError(caught instanceof ApiError ? caught.message : 'Oznam sa nepodarilo odstrániť.')
    } finally {
      setDeleteBusy(false)
    }
  }

  return (
    <section className="content-page page-stack" aria-labelledby="info-title">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Ručne spravovaný obsah</p>
          <h1 id="info-title">INFO oznamy</h1>
          <p>Trvalejšie informácie s vlastnou platnosťou a voliteľným thumbnailom.</p>
        </div>
        <button type="button" onClick={() => setEditing('new')}>
          Pridať INFO oznam
        </button>
      </header>

      {loading && <ContentState text="Načítavam INFO oznamy…" />}
      {error && <ContentState text={error.message} retry={() => void reload()} />}
      {!loading && !error && active.length === 0 && (
        <div className="content-empty">
          <strong>Zatiaľ tu nie je žiadny INFO oznam.</strong>
          <p>Vytvorte prvý oznam, nastavte jeho platnosť a podľa potreby pridajte obrázok.</p>
          <button type="button" onClick={() => setEditing('new')}>
            Vytvoriť prvý oznam
          </button>
        </div>
      )}
      {!loading && !error && active.length > 0 && (
        <div className="record-grid">
          {active.map((item) => (
            <article className="record-card" key={item.id}>
              {item.image_url && (
                <img className="record-thumbnail" src={item.image_url} alt="" loading="lazy" />
              )}
              <div className="record-card-top">
                <span className={`status-pill ${item.active ? 'status-ready' : 'status-muted'}`}>
                  {item.active ? 'Aktívny' : 'Pozastavený'}
                </span>
                <span className="record-validity">
                  {formatDate(item.valid_from)} – {formatDate(item.valid_until)}
                </span>
              </div>
              <h2>{item.title}</h2>
              <p>{item.description}</p>
              <div className="record-actions">
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
        <InfoEditor
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
          detail="Oznam prestane byť dostupný pre budúce publikácie. Operácia sa zaznamená do auditu."
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

export function InfoEditor({
  record,
  onClose,
  onSaved,
}: {
  record: InfoAnnouncementRecord | null
  onClose: () => void
  onSaved: () => Promise<void>
}) {
  const today = new Date().toISOString().slice(0, 10)
  const [title, setTitle] = useState(record?.title ?? '')
  const [description, setDescription] = useState(record?.description ?? '')
  const [validFrom, setValidFrom] = useState(record?.valid_from ?? today)
  const [validUntil, setValidUntil] = useState(record?.valid_until ?? today)
  const [linkUrl, setLinkUrl] = useState(record?.link_url ?? '')
  const [imageUrl, setImageUrl] = useState(record?.image_url ?? '')
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [active, setActive] = useState(record?.active ?? true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  async function chooseImage(file: File | undefined) {
    if (!file) return
    setUploading(true)
    setUploadError(null)
    try {
      const uploaded = await uploadInfoImage(file)
      setImageUrl(uploaded.image_url)
    } catch (caught) {
      setUploadError(
        caught instanceof ApiError ? caught.message : 'Obrázok sa nepodarilo spracovať.',
      )
    } finally {
      setUploading(false)
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await saveInfoAnnouncement(
        {
          title: title.trim(),
          description: description.trim(),
          valid_from: validFrom,
          valid_until: validUntil,
          link_url: optional(linkUrl),
          image_url: optional(imageUrl),
          active,
          ...(record ? { expected_version: record.version } : {}),
        },
        record?.id,
      )
      await onSaved()
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught : new ApiError('Oznam sa nepodarilo uložiť.', 0, null),
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <ContentDialog
      eyebrow={record ? 'Úprava INFO oznamu' : 'Nový INFO oznam'}
      title={record?.title ?? 'Pridať INFO oznam'}
      subtitle="Platnosť zahŕňa aj posledný zvolený deň."
      busy={busy || uploading}
      onClose={onClose}
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
        <label className="form-field">
          <span>Popis</span>
          <textarea
            required
            maxLength={4096}
            rows={7}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
          <small className="character-count">{description.length} / 4096</small>
        </label>
        <div className="form-columns">
          <label className="form-field">
            <span>Platí od</span>
            <input
              type="date"
              required
              value={validFrom}
              onChange={(event) => setValidFrom(event.target.value)}
            />
          </label>
          <label className="form-field">
            <span>Platí do</span>
            <input
              type="date"
              required
              min={validFrom}
              value={validUntil}
              onChange={(event) => setValidUntil(event.target.value)}
            />
          </label>
        </div>
        <label className="form-field">
          <span>Odkaz (voliteľný)</span>
          <input
            type="url"
            placeholder="https://…"
            value={linkUrl}
            onChange={(event) => setLinkUrl(event.target.value)}
          />
        </label>
        <div className="form-field">
          <span>Obrázok oznamu (voliteľný)</span>
          {imageUrl ? (
            <div className="image-upload-preview">
              <img src={imageUrl} alt="Náhľad obrázka INFO oznamu" />
              <div>
                <strong>Obrázok je pripravený</strong>
                <small>Server ho upravil na bezpečný rozmer a formát.</small>
                <div className="image-upload-actions">
                  <label className="secondary-button file-button">
                    <ImagePlus aria-hidden="true" />
                    Nahradiť
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      disabled={uploading}
                      onChange={(event) => void chooseImage(event.target.files?.[0])}
                    />
                  </label>
                  <button
                    className="quiet-danger"
                    type="button"
                    disabled={uploading}
                    onClick={() => setImageUrl('')}
                  >
                    <X aria-hidden="true" />
                    Odobrať
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <label
              className={`image-upload-zone${uploading ? ' is-uploading' : ''}`}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault()
                void chooseImage(event.dataTransfer.files[0])
              }}
            >
              <UploadCloud aria-hidden="true" />
              <strong>{uploading ? 'Spracúvam obrázok…' : 'Nahrať obrázok'}</strong>
              <small>Potiahnite ho sem alebo vyberte súbor · JPEG, PNG či WebP · max. 8 MB</small>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                disabled={uploading}
                onChange={(event) => void chooseImage(event.target.files?.[0])}
              />
            </label>
          )}
          {uploadError && (
            <small className="upload-error" role="alert">
              {uploadError}
            </small>
          )}
        </div>
        <label className="switch-row">
          <span>
            <strong>Oznam je aktívny</strong>
            <small>Neaktívny oznam sa nebude publikovať.</small>
          </span>
          <input
            type="checkbox"
            checked={active}
            onChange={(event) => setActive(event.target.checked)}
          />
        </label>
        {error && (
          <div className="form-alert" role="alert">
            <strong>Oznam sa nepodarilo uložiť</strong>
            <p>{error.message}</p>
            {error.status === 409 && (
              <button
                className="secondary-button alert-action"
                type="button"
                onClick={() => void onSaved()}
              >
                Načítať aktuálny záznam
              </button>
            )}
          </div>
        )}
        <footer className="drawer-actions">
          <button
            className="secondary-button"
            type="button"
            onClick={onClose}
            disabled={busy || uploading}
          >
            Zrušiť
          </button>
          <button type="submit" disabled={busy || uploading}>
            {uploading ? 'Spracúvam obrázok…' : busy ? 'Ukladám…' : 'Uložiť oznam'}
          </button>
        </footer>
      </form>
    </ContentDialog>
  )
}

function ContentState({ text, retry }: { text: string; retry?: () => void }) {
  return (
    <div className="content-empty" role="status">
      <strong>{text}</strong>
      {retry && <button onClick={retry}>Skúsiť znova</button>}
    </div>
  )
}

function optional(value: string) {
  return value.trim() || null
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('sk-SK').format(new Date(`${value}T12:00:00`))
}
