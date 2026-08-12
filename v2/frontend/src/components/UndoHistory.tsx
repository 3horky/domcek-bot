import { History, RotateCcw } from 'lucide-react'
import { useEffect, useState } from 'react'

import {
  ApiError,
  getUndoOperations,
  type UndoOperation,
  undoDiscordOperation,
} from '../api/client'
import { Button } from './ui/button'

export function UndoHistory({
  scope,
  revision,
  onChanged,
}: {
  scope: 'roles' | 'channels'
  revision: number
  onChanged: () => Promise<void>
}) {
  const [items, setItems] = useState<UndoOperation[]>([])
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    void getUndoOperations(scope, controller.signal)
      .then(setItems)
      .catch((caught) => {
        if (!controller.signal.aborted)
          setError(caught instanceof ApiError ? caught.message : 'Vratné zmeny sa nenačítali.')
      })
    return () => controller.abort()
  }, [revision, scope])

  if (!items.length && !error) return null
  return (
    <section className="undo-history" aria-labelledby={`undo-${scope}-title`}>
      <div className="undo-history-heading">
        <History aria-hidden="true" />
        <div>
          <h2 id={`undo-${scope}-title`}>Vratné zmeny</h2>
          <p>Zostanú dostupné aj po obnovení stránky, pokiaľ je návrat stále bezpečný.</p>
        </div>
      </div>
      {error && <p role="alert">{error}</p>}
      <div className="undo-history-list">
        {items.map((item) => (
          <article key={item.id}>
            <div>
              <strong>{undoTitle(item)}</strong>
              <small>{undoDescription(item)}</small>
            </div>
            <Button
              variant="outline"
              disabled={busyId !== null}
              onClick={() => {
                setBusyId(item.id)
                setError(null)
                void undoDiscordOperation(item.id)
                  .then(async () => {
                    setItems((current) => current.filter((value) => value.id !== item.id))
                    await onChanged()
                  })
                  .catch((caught) =>
                    setError(
                      caught instanceof ApiError
                        ? caught.message
                        : 'Zmenu sa nepodarilo bezpečne vrátiť.',
                    ),
                  )
                  .finally(() => setBusyId(null))
              }}
            >
              <RotateCcw aria-hidden="true" />
              {busyId === item.id ? 'Vraciam…' : 'Vrátiť späť'}
            </Button>
          </article>
        ))}
      </div>
    </section>
  )
}

function undoTitle(item: UndoOperation) {
  if (item.operation_type === 'role_change')
    return `${String(item.after_snapshot.member_name ?? 'Človek')} · ${String(item.after_snapshot.role ?? 'rola')}`
  if (item.operation_type === 'channel_create')
    return `Vytvorený kanál #${String(item.after_snapshot.name ?? item.object_id)}`
  return `Archivovaný kanál #${String(item.before_snapshot.name ?? item.object_id)}`
}

function undoDescription(item: UndoOperation) {
  if (item.operation_type === 'role_change')
    return item.after_snapshot.enabled ? 'Oprávnenie bolo udelené.' : 'Oprávnenie bolo odobrané.'
  if (item.operation_type === 'channel_create') return 'Odstráni sa iba nezmenený prázdny kanál.'
  return 'Obnoví sa iba kanál, ktorý sa od archivácie nezmenil.'
}
