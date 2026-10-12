import { useCallback, useEffect, useRef, useState } from 'react'
import { Trash2, Upload } from 'lucide-react'
import {
  deleteDocument,
  fetchDocuments,
  uploadDocument,
  type DocumentResponse,
} from '../api/client'
import StatusBadge from '../components/StatusBadge'
import Spinner from '../components/Spinner'
import { useDocumentPoller } from '../hooks/useDocumentPoller'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function DocumentsPage() {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [documents, setDocuments] = useState<DocumentResponse[]>([])
  const [loadingDocs, setLoadingDocs] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [uploading, setUploading] = useState(false)
  const [uploadFilename, setUploadFilename] = useState<string | null>(null)

  // { [id]: 'pending' | 'confirmed' } — delete confirmation state per row
  const [deleteState, setDeleteState] = useState<Record<string, 'pending' | 'confirming'>>({})

  // ── Load documents ──────────────────────────────────────────────────────────

  const loadDocuments = useCallback(async () => {
    try {
      const docs = await fetchDocuments()
      setDocuments(docs)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents.')
    } finally {
      setLoadingDocs(false)
    }
  }, [])

  useEffect(() => {
    void loadDocuments()
  }, [loadDocuments])

  // ── Poll while any doc is processing ────────────────────────────────────────

  useDocumentPoller(documents, () => void loadDocuments())

  // ── Upload ──────────────────────────────────────────────────────────────────

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    // Reset input so same file can be re-uploaded
    e.target.value = ''

    setUploading(true)
    setUploadFilename(file.name)
    setError(null)

    try {
      const doc = await uploadDocument(file)
      setDocuments((prev) => [doc, ...prev])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed.')
    } finally {
      setUploading(false)
      setUploadFilename(null)
    }
  }

  // ── Delete ──────────────────────────────────────────────────────────────────

  function requestDelete(id: string) {
    setDeleteState((prev) => ({ ...prev, [id]: 'confirming' }))
  }

  function cancelDelete(id: string) {
    setDeleteState((prev) => {
      const next = { ...prev }
      delete next[id]
      return next
    })
  }

  async function confirmDelete(id: string) {
    setDeleteState((prev) => {
      const next = { ...prev }
      delete next[id]
      return next
    })
    try {
      await deleteDocument(id)
      setDocuments((prev) => prev.filter((d) => d.id !== id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed.')
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 bg-white px-8 py-5">
        <div>
          <h1 className="text-xl font-bold text-gray-900">My Documents</h1>
          <p className="text-sm text-gray-500">
            Upload PDFs to make them searchable by the assistant
          </p>
        </div>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="flex items-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-dark disabled:opacity-60"
        >
          {uploading ? <Spinner size={16} className="text-white" /> : <Upload size={16} />}
          Upload PDF
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={handleFileChange}
        />
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-8 py-6">
        {/* Error */}
        {error && (
          <div className="mb-4 flex items-center justify-between rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="font-medium underline">
              Dismiss
            </button>
          </div>
        )}

        {/* Upload progress card */}
        {uploading && uploadFilename && (
          <div className="mb-4 flex items-center gap-4 rounded-xl border border-brand-light bg-brand-light/50 px-5 py-4">
            <Spinner size={20} className="text-brand" />
            <div>
              <p className="text-sm font-medium text-brand-dark">Uploading…</p>
              <p className="text-xs text-gray-500 truncate max-w-xs">{uploadFilename}</p>
            </div>
          </div>
        )}

        {/* Loading skeleton */}
        {loadingDocs ? (
          <div className="flex justify-center pt-16">
            <Spinner size={32} className="text-brand" />
          </div>
        ) : documents.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center gap-4 pt-24 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gray-100">
              <span className="text-3xl">📄</span>
            </div>
            <p className="text-lg font-semibold text-gray-700">No documents yet</p>
            <p className="max-w-xs text-sm text-gray-400">
              Upload a PDF to get started — the assistant will index it and make it
              searchable.
            </p>
          </div>
        ) : (
          /* Document table */
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  {['Filename', 'Status', 'Chunks', 'Uploaded', ''].map((h) => (
                    <th
                      key={h}
                      className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {documents.map((doc) => (
                  <tr key={doc.id} className="transition-colors hover:bg-gray-50">
                    <td className="max-w-xs px-5 py-3.5">
                      <p className="truncate text-sm font-medium text-gray-800">
                        {doc.filename}
                      </p>
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="px-5 py-3.5 text-sm text-gray-500">
                      {doc.chunk_count ?? '—'}
                    </td>
                    <td className="px-5 py-3.5 text-sm text-gray-500">
                      {formatDate(doc.created_at)}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      {deleteState[doc.id] === 'confirming' ? (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => void confirmDelete(doc.id)}
                            className="rounded px-2.5 py-1 text-xs font-semibold text-white bg-red-500 hover:bg-red-600 transition-colors"
                          >
                            Confirm
                          </button>
                          <button
                            onClick={() => cancelDelete(doc.id)}
                            className="rounded px-2.5 py-1 text-xs font-semibold text-gray-600 bg-gray-100 hover:bg-gray-200 transition-colors"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => requestDelete(doc.id)}
                          className="rounded p-1.5 text-gray-400 transition-colors hover:bg-red-50 hover:text-red-500"
                          title="Delete document"
                        >
                          <Trash2 size={15} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
