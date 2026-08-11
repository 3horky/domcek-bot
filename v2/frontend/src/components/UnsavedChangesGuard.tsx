import { useCallback } from 'react'
import { useBeforeUnload, useBlocker } from 'react-router-dom'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from './ui/alert-dialog'

export function UnsavedChangesGuard({
  active,
  title = 'Zahodiť neuložené zmeny?',
  description = 'Zmeny, ktoré ste ešte neuložili, sa stratia.',
}: {
  active: boolean
  title?: string
  description?: string
}) {
  useBeforeUnload(
    useCallback(
      (event) => {
        if (!active) return
        event.preventDefault()
      },
      [active],
    ),
  )
  const blocker = useBlocker(active)
  const blocked = blocker.state === 'blocked'

  return (
    <AlertDialog
      open={blocked}
      onOpenChange={(open) => {
        if (!open && blocker.state === 'blocked') blocker.reset()
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel
            onClick={() => {
              if (blocker.state === 'blocked') blocker.reset()
            }}
          >
            Zostať a dokončiť
          </AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            onClick={() => {
              if (blocker.state === 'blocked') blocker.proceed()
            }}
          >
            Zahodiť zmeny
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
