import { useCallback, useEffect, useState } from 'react'

import { ApiError } from '../api/client'

export function useApiList<T>(loader: (signal?: AbortSignal) => Promise<T[]>) {
  const [items, setItems] = useState<T[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | null>(null)

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true)
      setError(null)
      try {
        setItems(await loader(signal))
      } catch (caught) {
        if (signal?.aborted) return
        setError(
          caught instanceof ApiError
            ? caught
            : new ApiError('Obsah sa nepodarilo načítať.', 0, null),
        )
      } finally {
        if (!signal?.aborted) setLoading(false)
      }
    },
    [loader],
  )

  useEffect(() => {
    const controller = new AbortController()
    void loader(controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setItems(value)
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return
        setError(
          caught instanceof ApiError
            ? caught
            : new ApiError('Obsah sa nepodarilo načítať.', 0, null),
        )
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [loader])

  return { items, loading, error, reload: () => load() }
}
