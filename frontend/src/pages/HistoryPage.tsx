import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ExternalLink, MessageSquare } from 'lucide-react'
import { fetchConversations, type ConversationSummary } from '../api/client'
import Spinner from '../components/Spinner'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function HistoryPage() {
  const navigate = useNavigate()

  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchConversations()
      .then(setConversations)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load history.'),
      )
      .finally(() => setLoading(false))
  }, [])

  function openConversation(id: string) {
    navigate(`/chat?conv=${id}`)
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-8 py-5">
        <h1 className="text-xl font-bold text-gray-900">Conversation History</h1>
        <p className="text-sm text-gray-500">
          All your past conversations with the assistant
        </p>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-8 py-6">
        {/* Error */}
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center pt-16">
            <Spinner size={32} className="text-brand" />
          </div>
        ) : conversations.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center gap-5 pt-24 text-center">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-brand-light">
              <MessageSquare size={36} className="text-brand" />
            </div>
            <div>
              <p className="text-lg font-semibold text-gray-700">
                No conversations yet
              </p>
              <p className="mt-1 text-sm text-gray-400">
                Start chatting — your conversations will appear here.
              </p>
            </div>
            <button
              onClick={() => navigate('/chat')}
              className="flex items-center gap-2 rounded-lg bg-brand px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-dark"
            >
              Start chatting
            </button>
          </div>
        ) : (
          /* Conversation cards */
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className="flex flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md"
              >
                {/* Icon + date */}
                <div className="mb-4 flex items-start gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-light">
                    <MessageSquare size={18} className="text-brand" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-gray-800">
                      Conversation
                    </p>
                    <p className="text-xs text-gray-400">
                      {formatDateTime(conv.created_at)}
                    </p>
                  </div>
                </div>

                {/* Conversation ID (truncated) */}
                <p className="mb-4 truncate text-xs text-gray-400" title={conv.id}>
                  ID: {conv.id}
                </p>

                {/* CTA */}
                <button
                  onClick={() => openConversation(conv.id)}
                  className="mt-auto flex items-center justify-center gap-2 rounded-lg border border-brand px-4 py-2 text-sm font-semibold text-brand transition-colors hover:bg-brand hover:text-white"
                >
                  <ExternalLink size={14} />
                  Open in Chat
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
