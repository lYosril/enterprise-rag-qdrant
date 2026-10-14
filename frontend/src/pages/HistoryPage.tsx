import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ExternalLink, MessageSquare, Clock, ArrowRight } from 'lucide-react'
import { getConversations } from '../api/chat'
import type { ConversationSummary } from '../types'
import Spinner from '../components/Spinner'

function formatDateTime(iso: string) {
  try {
    return new Date(iso).toLocaleString(undefined, {
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

export const HistoryPage: React.FC = () => {
  const navigate = useNavigate()
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getConversations()
      .then(setConversations)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load conversation history'),
      )
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="flex flex-col h-full overflow-hidden bg-slate-50">
      <div className="border-b border-slate-200 bg-white px-8 py-5">
        <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
          <Clock className="h-5 w-5 text-emerald-600" />
          Conversation History
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Review, reopen, and continue past grounded question & answering sessions
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-8 py-6">
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 p-3 text-xs text-red-700 border border-red-200">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center pt-20">
            <Spinner size={32} className="text-emerald-600" />
          </div>
        ) : conversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-4 pt-24 text-center max-w-sm mx-auto">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-600 shadow-xs">
              <MessageSquare className="h-8 w-8" />
            </div>
            <h3 className="text-base font-bold text-slate-800">No conversations yet</h3>
            <p className="text-xs text-slate-500">
              Your previous search and conversation threads will be archived and easily accessible here.
            </p>
            <button
              type="button"
              onClick={() => navigate('/chat')}
              className="mt-2 inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-700 transition shadow-xs"
            >
              Start new chat <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-xs hover:border-emerald-300 hover:shadow-md transition-all"
              >
                <div className="mb-4 flex items-start gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
                    <MessageSquare className="h-5 w-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-slate-800 truncate">
                      Session {conv.id.slice(0, 8)}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {formatDateTime(conv.created_at)}
                    </p>
                  </div>
                </div>

                <div className="mt-auto pt-3 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-[11px] font-mono text-slate-400 truncate max-w-[120px]">
                    {conv.id.slice(0, 12)}...
                  </span>
                  <button
                    type="button"
                    onClick={() => navigate(`/chat?conv=${conv.id}`)}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-100 transition"
                  >
                    Open <ExternalLink className="h-3 w-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default HistoryPage
