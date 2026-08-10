import { useCallback, useEffect, useState } from 'react'

import { ApiError, getPublicationDraft, type PublicationDraft } from '../api/client'

export function usePublicationDraft() {
  const [draft, setDraft] = useState<PublicationDraft | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    setError(null)
    try {
      setDraft(await getPublicationDraft(signal))
    } catch (value) {
      if (signal?.aborted) return
      setError(
        value instanceof ApiError ? value : new ApiError('Draft sa nepodarilo načítať.', 0, null),
      )
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void getPublicationDraft(controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setDraft(value)
      })
      .catch((value: unknown) => {
        if (controller.signal.aborted) return
        setError(
          value instanceof ApiError ? value : new ApiError('Draft sa nepodarilo načítať.', 0, null),
        )
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [])

  return { draft, error, loading, reload: () => load() }
}
