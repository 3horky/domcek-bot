import { AlertTriangle, Inbox, LoaderCircle, RefreshCw } from 'lucide-react'
import type { ReactNode } from 'react'

import { Button } from './ui/button'

export function LoadingState({ label }: { label: string }) {
  return (
    <div className="settings-loading" role="status" aria-live="polite">
      <LoaderCircle className="spin" aria-hidden="true" /> {label}
    </div>
  )
}

export function LoadErrorState({
  title = 'Údaje sa nepodarilo načítať',
  detail,
  onRetry,
}: {
  title?: string
  detail: string
  onRetry: () => void
}) {
  return (
    <div className="content-empty content-empty-error" role="alert">
      <AlertTriangle aria-hidden="true" />
      <strong>{title}</strong>
      <p>{detail}</p>
      <Button variant="outline" onClick={onRetry}>
        <RefreshCw aria-hidden="true" /> Skúsiť znova
      </Button>
    </div>
  )
}

export function EmptyState({
  title,
  detail,
  action,
}: {
  title: string
  detail: string
  action?: ReactNode
}) {
  return (
    <div className="content-empty" role="status">
      <Inbox aria-hidden="true" />
      <strong>{title}</strong>
      <p>{detail}</p>
      {action}
    </div>
  )
}
