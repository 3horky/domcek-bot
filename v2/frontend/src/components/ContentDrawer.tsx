import type { ReactNode } from 'react'
import { Trash2 } from 'lucide-react'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

export function ContentDialog({
  eyebrow,
  title,
  subtitle,
  busy,
  onClose,
  children,
}: {
  eyebrow: string
  title: string
  subtitle?: string
  busy: boolean
  onClose: () => void
  children: ReactNode
}) {
  return (
    <Dialog
      open
      disablePointerDismissal={busy}
      onOpenChange={(open) => {
        if (!open && !busy) onClose()
      }}
    >
      <DialogContent className="content-dialog" showCloseButton={!busy}>
        <DialogHeader className="content-dialog-header">
          <p className="eyebrow">{eyebrow}</p>
          <DialogTitle>{title}</DialogTitle>
          {subtitle && <DialogDescription>{subtitle}</DialogDescription>}
        </DialogHeader>
        {children}
      </DialogContent>
    </Dialog>
  )
}

export function ConfirmDialog({
  title,
  detail,
  busy,
  onCancel,
  onConfirm,
  error,
  confirmLabel = 'Odstrániť',
  cancelLabel = 'Ponechať',
}: {
  title: string
  detail: string
  busy: boolean
  onCancel: () => void
  onConfirm: () => void
  error?: string | null
  confirmLabel?: string
  cancelLabel?: string
}) {
  return (
    <AlertDialog
      open
      onOpenChange={(open) => {
        if (!open && !busy) onCancel()
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogMedia className="delete-dialog-icon">
            <Trash2 />
          </AlertDialogMedia>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{detail}</AlertDialogDescription>
        </AlertDialogHeader>
        {error && (
          <p className="confirm-error" role="alert">
            {error}
          </p>
        )}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={busy}>{cancelLabel}</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={onConfirm} disabled={busy}>
            {busy ? 'Pracujem…' : confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
