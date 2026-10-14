import React, { useCallback, useEffect, useState, useMemo } from 'react'
import {
  Trash2,
  RotateCw,
  Search,
  Filter,
  FileText,
  AlertTriangle,
  RefreshCw,
  CheckCircle,
} from 'lucide-react'
import {
  getDocuments,
  deleteDocument,
  retryDocument,
  reconcileDocuments,
} from '../api/documents'
import type { DocumentResponse } from '../types'
import StatusBadge from '../components/StatusBadge'
import Spinner from '../components/Spinner'
import FileUploader from '../components/FileUploader'
import { useDocumentPoller } from '../hooks/useDocumentPoller'

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export const DocumentsPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [retryingIds, setRetryingIds] = useState<Record<string, boolean>>({})
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const [reconciling, setReconciling] = useState(false)
  const [reconcileResult, setReconcileResult] = useState<string | null>(null)

  const loadDocuments = useCallback(async () => {
    try {
      const data = await getDocuments()
      setDocuments(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load documents'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadDocuments()
  }, [loadDocuments])

  // Poll while any document is in 'processing' or 'uploaded' state
  useDocumentPoller(documents, () => void loadDocuments())

  const handleRetry = async (id: string) => {
    setRetryingIds((prev) => ({ ...prev, [id]: true }))
    try {
      await retryDocument(id)
      await loadDocuments()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Retry failed'
      setError(msg)
    } finally {
      setRetryingIds((prev) => ({ ...prev, [id]: false }))
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteDocument(id)
      setDocuments((prev) => prev.filter((d) => d.id !== id))
      setDeleteConfirmId(null)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Delete failed'
      setError(msg)
    }
  }

  const handleReconcile = async () => {
    setReconciling(true)
    setReconcileResult(null)
    try {
      const res = (await reconcileDocuments()) as {
        inconsistencies_found?: number
        total_documents?: number
      }
      setReconcileResult(
        `Reconciliation complete: checked ${res.total_documents ?? documents.length} docs, found ${res.inconsistencies_found ?? 0} inconsistencies.`,
      )
      await loadDocuments()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Reconciliation failed'
      setError(msg)
    } finally {
      setReconciling(false)
    }
  }

  // Filter & Search
  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      const matchesSearch = doc.filename
        .toLowerCase()
        .includes(searchTerm.toLowerCase().trim())
      const matchesStatus =
        statusFilter === 'all' || doc.status === statusFilter
      return matchesSearch && matchesStatus
    })
  }, [documents, searchTerm, statusFilter])

  return (
    <div className="flex flex-col h-full overflow-hidden bg-slate-50">
      {/* Header */}
      <div className="border-b border-slate-200 bg-white px-8 py-5">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-800">Document Library</h1>
            <p className="text-xs text-slate-500 mt-1">
              Upload, monitor ingestion status, and manage corporate PDF knowledge
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleReconcile}
              disabled={reconciling}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition shadow-xs disabled:opacity-50"
              title="Verify Qdrant vectors match PostgreSQL state"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${reconciling ? 'animate-spin' : ''}`} />
              Reconcile Vectors
            </button>
            <button
              type="button"
              onClick={() => void loadDocuments()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition shadow-xs"
            >
              <RotateCw className="h-3.5 w-3.5" />
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Main Body */}
      <div className="flex-1 overflow-y-auto px-8 py-6 space-y-6">
        {/* Reconcile notice */}
        {reconcileResult && (
          <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800 animate-in fade-in">
            <CheckCircle className="h-4 w-4 text-emerald-600 shrink-0" />
            <span>{reconcileResult}</span>
          </div>
        )}

        {/* Global Error Banner */}
        {error && (
          <div className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 animate-in fade-in">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-red-600 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              type="button"
              onClick={() => setError(null)}
              className="font-bold underline hover:text-red-900"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Upload Zone */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <h2 className="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
            <FileText className="h-4 w-4 text-emerald-600" />
            Ingest New Knowledge Document
          </h2>
          <FileUploader onUploadSuccess={() => void loadDocuments()} />
        </div>

        {/* Search & Filter Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search documents by name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-xs text-slate-700 focus:border-emerald-500 focus:outline-hidden focus:ring-1 focus:ring-emerald-500"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Filter className="h-4 w-4 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 focus:border-emerald-500 focus:outline-hidden"
            >
              <option value="all">All Statuses ({documents.length})</option>
              <option value="indexed">Indexed</option>
              <option value="processing">Processing</option>
              <option value="uploaded">Uploaded</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>

        {/* Document Table */}
        {loading ? (
          <div className="flex justify-center py-16">
            <Spinner size={32} className="text-emerald-600" />
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 bg-white p-12 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 mb-3">
              <FileText className="h-6 w-6" />
            </div>
            <h3 className="text-sm font-semibold text-slate-700">No documents found</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              {searchTerm || statusFilter !== 'all'
                ? 'Try adjusting your search query or status filter.'
                : 'Upload a PDF document above to start indexing enterprise knowledge.'}
            </p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs">
            <table className="min-w-full divide-y divide-slate-100">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Document
                  </th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Vectors / Chunks
                  </th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Upload Date
                  </th>
                  <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredDocuments.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <FileText className="h-4 w-4 text-emerald-600 shrink-0" />
                        <div>
                          <p className="text-xs font-semibold text-slate-800 truncate max-w-xs md:max-w-md" title={doc.filename}>
                            {doc.filename}
                          </p>
                          {doc.error_message && (
                            <p className="text-[11px] text-red-600 truncate max-w-xs mt-0.5" title={doc.error_message}>
                              Error: {doc.error_message}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-600 font-medium">
                      {doc.chunk_count > 0 ? `${doc.chunk_count} chunks` : '—'}
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-500">
                      {formatDate(doc.created_at)}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {/* Retry action for failed documents */}
                        {doc.status === 'failed' && (
                          <button
                            type="button"
                            onClick={() => handleRetry(doc.id)}
                            disabled={retryingIds[doc.id]}
                            className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700 hover:bg-amber-100 transition"
                            title="Retry document ingestion"
                          >
                            <RotateCw className={`h-3 w-3 ${retryingIds[doc.id] ? 'animate-spin' : ''}`} />
                            Retry
                          </button>
                        )}

                        {/* Delete confirmation */}
                        {deleteConfirmId === doc.id ? (
                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              onClick={() => handleDelete(doc.id)}
                              className="rounded-md bg-red-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-red-700 transition"
                            >
                              Confirm
                            </button>
                            <button
                              type="button"
                              onClick={() => setDeleteConfirmId(null)}
                              className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-200 transition"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setDeleteConfirmId(doc.id)}
                            className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600 transition"
                            title="Delete document"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
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

export default DocumentsPage
