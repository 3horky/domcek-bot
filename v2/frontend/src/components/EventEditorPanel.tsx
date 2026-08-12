import { useEffect, useMemo, useRef, useState } from 'react'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ConfirmDialog } from './ContentDrawer'

import {
  ApiError,
  type DescriptionState,
  type DraftItem,
  type InclusionDecision,
  getPublicationDraft,
  updateEventOverride,
  updateSeriesOverride,
} from '../api/client'

type EditScope = 'instance' | 'series'

interface EventEditorPanelProps {
  item: DraftItem
  canForceInclusion: boolean
  onClose: () => void
  onSaved: () => Promise<void> | void
}

export function EventEditorPanel({
  item,
  canForceInclusion,
  onClose,
  onSaved,
}: EventEditorPanelProps) {
  const draftKey = `carlo:calendar-event:${item.source_id}`

  const initial = useMemo(
    () => ({
      scope: 'instance' as EditScope,
      publicTitle: item.instance_public_title ?? '',
      descriptionState: initialDescriptionState(item),
      publicDescription: initialDescription(item),
      inclusion: item.inclusion_decision,
    }),
    [item],
  )
  const recovered = useMemo(() => readEventDraft<typeof initial>(draftKey), [draftKey])
  const [scope, setScope] = useState<EditScope>(recovered?.scope ?? initial.scope)
  const [publicTitle, setPublicTitle] = useState(recovered?.publicTitle ?? initial.publicTitle)
  const [descriptionState, setDescriptionState] = useState<DescriptionState>(
    recovered?.descriptionState ?? initial.descriptionState,
  )
  const [publicDescription, setPublicDescription] = useState(
    recovered?.publicDescription ?? initial.publicDescription,
  )
  const [inclusion, setInclusion] = useState<InclusionDecision>(
    recovered?.inclusion ?? initial.inclusion,
  )
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [instanceVersion, setInstanceVersion] = useState(item.instance_override_version)
  const [seriesVersion, setSeriesVersion] = useState(item.series_override_version)
  const [discarding, setDiscarding] = useState(false)
  const [versionNotice, setVersionNotice] = useState<string | null>(null)
  const saveInFlight = useRef(false)
  const values = useMemo(
    () => ({ scope, publicTitle, descriptionState, publicDescription, inclusion }),
    [descriptionState, inclusion, publicDescription, publicTitle, scope],
  )
  const dirty = JSON.stringify(values) !== JSON.stringify(initial)

  useEffect(() => {
    if (dirty) window.sessionStorage.setItem(draftKey, JSON.stringify(values))
    else window.sessionStorage.removeItem(draftKey)
  }, [dirty, draftKey, values])

  function changeScope(nextScope: EditScope) {
    setScope(nextScope)
    setError(null)
    if (nextScope === 'series') {
      setPublicTitle(item.series_public_title ?? '')
      setDescriptionState(seriesDescriptionState(item))
      setPublicDescription(seriesDescription(item))
    } else {
      setPublicTitle(item.instance_public_title ?? '')
      setDescriptionState(initialDescriptionState(item))
      setPublicDescription(initialDescription(item))
    }
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (saveInFlight.current) return
    saveInFlight.current = true
    setSaving(true)
    setError(null)
    setVersionNotice(null)
    const body = {
      expected_version: scope === 'series' ? seriesVersion : instanceVersion,
      public_title: cleanOptional(publicTitle),
      description_state: descriptionState,
      public_description: descriptionState === 'custom' ? cleanOptional(publicDescription) : null,
      ...(scope === 'instance' && canForceInclusion ? { inclusion_decision: inclusion } : {}),
    }
    try {
      if (scope === 'series') await updateSeriesOverride(item.source_id, body)
      else await updateEventOverride(item.source_id, body)
      window.sessionStorage.removeItem(draftKey)
      await onSaved()
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught : new ApiError('Úpravu sa nepodarilo uložiť.', 0, null),
      )
    } finally {
      saveInFlight.current = false
      setSaving(false)
    }
  }

  async function refreshVersion() {
    try {
      const latestDraft = await getPublicationDraft()
      const latest = latestDraft.editor_events.find((entry) => entry.source_id === item.source_id)
      if (!latest) {
        setVersionNotice('Udalosť už nie je v najbližšom období. Vaše hodnoty zostali zachované.')
        return
      }
      setInstanceVersion(latest.instance_override_version)
      setSeriesVersion(latest.series_override_version)
      setError(null)
      setVersionNotice(
        'Načítaná je novšia verzia udalosti. Vaše rozpracované hodnoty zostali zachované.',
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
    <Dialog
      open
      disablePointerDismissal={saving}
      onOpenChange={(open) => {
        if (!open && !saving) requestClose()
      }}
    >
      <DialogContent className="content-dialog event-editor-dialog" showCloseButton={!saving}>
        <DialogHeader className="content-dialog-header">
          <p className="eyebrow">Redakčná úprava</p>
          <DialogTitle>{item.source_title ?? item.title}</DialogTitle>
          <DialogDescription>{item.display_time ?? 'Čas nie je uvedený'}</DialogDescription>
        </DialogHeader>

        <form className="drawer-form" onSubmit={submit}>
          {item.is_recurring && (
            <fieldset className="choice-section">
              <legend>Rozsah zmeny</legend>
              <div className="segmented-control">
                <label>
                  <input
                    type="radio"
                    name="scope"
                    value="instance"
                    checked={scope === 'instance'}
                    onChange={() => changeScope('instance')}
                  />
                  <span>Len tento výskyt</span>
                </label>
                <label>
                  <input
                    type="radio"
                    name="scope"
                    value="series"
                    checked={scope === 'series'}
                    onChange={() => changeScope('series')}
                  />
                  <span>Tento a všetky budúce</span>
                </label>
              </div>
              <p className="field-hint">
                Minulé výskyty zostanú bez zmeny. Zaradenie sa vždy nastavuje iba pre tento
                konkrétny výskyt.
              </p>
            </fieldset>
          )}

          <label className="form-field">
            <span>Titulok oznamu</span>
            <input
              autoFocus
              value={publicTitle}
              maxLength={256}
              placeholder={item.source_title ?? item.title}
              onChange={(event) => setPublicTitle(event.target.value)}
            />
            <small>Prázdne pole použije názov z kalendára.</small>
          </label>

          <fieldset className="choice-section">
            <legend>Popis oznamu</legend>
            <div className="radio-cards">
              <label>
                <input
                  type="radio"
                  name="description-state"
                  checked={descriptionState === 'custom'}
                  onChange={() => setDescriptionState('custom')}
                />
                <span>
                  <strong>Vlastný popis</strong>
                  <small>Text upravíte nižšie.</small>
                </span>
              </label>
              <label>
                <input
                  type="radio"
                  name="description-state"
                  checked={descriptionState === 'inherit'}
                  onChange={() => setDescriptionState('inherit')}
                />
                <span>
                  <strong>Automaticky</strong>
                  <small>Použije sa systémové nastavenie.</small>
                </span>
              </label>
              <label>
                <input
                  type="radio"
                  name="description-state"
                  checked={descriptionState === 'intentionally_empty'}
                  onChange={() => setDescriptionState('intentionally_empty')}
                />
                <span>
                  <strong>Bez popisu</strong>
                  <small>Oznam ostane zámerne stručný.</small>
                </span>
              </label>
            </div>
          </fieldset>

          {descriptionState === 'custom' && (
            <label className="form-field">
              <span>Redakčný popis</span>
              <textarea
                value={publicDescription}
                maxLength={4096}
                rows={7}
                placeholder="Doplňte praktické informácie pre návštevníkov…"
                onChange={(event) => setPublicDescription(event.target.value)}
              />
              <small className="character-count">{publicDescription.length} / 4096</small>
            </label>
          )}

          {item.source_description && (
            <details className="source-description">
              <summary>Text z Google kalendára</summary>
              <p>{item.source_description}</p>
            </details>
          )}

          {scope === 'instance' && canForceInclusion && (
            <fieldset className="choice-section">
              <legend>Zaradenie do oznamov</legend>
              <select
                value={inclusion}
                onChange={(event) => setInclusion(event.target.value as InclusionDecision)}
              >
                <option value="auto">Automaticky podľa kalendára</option>
                <option value="force_include">Vždy zaradiť tento výskyt</option>
                <option value="force_exclude">Vylúčiť tento výskyt</option>
              </select>
            </fieldset>
          )}

          {error && (
            <div
              className={`form-alert${error.status === 409 ? ' conflict-alert' : ''}`}
              role="alert"
            >
              <strong>
                {error.status === 409
                  ? 'Medzitým vznikla novšia úprava'
                  : 'Zmenu sa nepodarilo uložiť'}
              </strong>
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
              {error.correlationId && <small>Referenčné ID: {error.correlationId}</small>}
            </div>
          )}
          {versionNotice && (
            <p className="form-notice" role="status">
              {versionNotice}
            </p>
          )}

          <footer className="drawer-actions">
            <button
              className="secondary-button"
              type="button"
              onClick={requestClose}
              disabled={saving}
            >
              Zrušiť
            </button>
            <button type="submit" disabled={saving}>
              {saving ? 'Ukladám…' : scope === 'series' ? 'Uložiť pre sériu' : 'Uložiť zmenu'}
            </button>
          </footer>
        </form>
        {discarding && (
          <ConfirmDialog
            title="Zahodiť redakčnú úpravu?"
            detail="Neuložený titulok, popis a zaradenie sa odstránia. Kalendárová udalosť zostane bez zmeny."
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
      </DialogContent>
    </Dialog>
  )
}

function cleanOptional(value: string): string | null {
  const clean = value.trim()
  return clean.length > 0 ? clean : null
}

function readEventDraft<T>(key: string): T | null {
  try {
    const value = window.sessionStorage.getItem(key)
    return value ? (JSON.parse(value) as T) : null
  } catch {
    window.sessionStorage.removeItem(key)
    return null
  }
}

function initialDescriptionState(item: DraftItem): DescriptionState {
  if (item.instance_description_state !== 'inherit') return item.instance_description_state
  if (item.instance_public_description) return 'custom'
  return item.source_description ? 'custom' : 'inherit'
}

function initialDescription(item: DraftItem): string {
  return item.instance_public_description ?? item.source_description ?? ''
}

function seriesDescriptionState(item: DraftItem): DescriptionState {
  if (item.series_description_state !== 'inherit') return item.series_description_state
  if (item.series_public_description) return 'custom'
  return item.source_description ? 'custom' : 'inherit'
}

function seriesDescription(item: DraftItem): string {
  return item.series_public_description ?? item.source_description ?? ''
}
