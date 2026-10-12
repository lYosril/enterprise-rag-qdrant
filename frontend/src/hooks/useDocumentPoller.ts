import { useEffect, useRef } from 'react'
import type { DocumentResponse } from '../api/client'

/**
 * Polls `onRefresh` every 3 seconds while any document has status
 * `'processing'` or `'uploaded'`. Clears the interval on unmount
 * or when no docs are pending.
 */
export function useDocumentPoller(
  documents: DocumentResponse[],
  onRefresh: () => void,
): void {
  const onRefreshRef = useRef(onRefresh)
  onRefreshRef.current = onRefresh

  useEffect(() => {
    const hasPending = documents.some(
      (d) => d.status === 'processing' || d.status === 'uploaded',
    )

    if (!hasPending) return

    const id = setInterval(() => {
      onRefreshRef.current()
    }, 3000)

    return () => clearInterval(id)
  }, [documents])
}
