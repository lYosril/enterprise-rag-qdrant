import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'
import { useSearchParams } from 'react-router-dom'
import { Paperclip, Plus, Send } from 'lucide-react'
import {
  fetchConversations,
  fetchMessages,
  sendChat,
  type ConversationSummary,
  type MessageResponse,
  type SourceResponse,
} from '../api/client'
import SourceCard from '../components/SourceCard'
import Spinner from '../components/Spinner'

// ─── Types for optimistic messages ───────────────────────────────────────────

interface LocalMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources: SourceResponse[] | null
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// ─── Source section (collapsible) ─────────────────────────────────────────────

function SourcesSection({ sources }: { sources: SourceResponse[] }) {
  const [open, setOpen] = useState(false)
  const [showAll, setShowAll] = useState(false)

  const visible = showAll ? sources : sources.slice(0, 3)

  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 text-xs font-medium text-brand hover:text-brand-dark"
      >
        {open ? '▾' : '▸'} {sources.length} source{sources.length !== 1 ? 's' : ''}
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {visible.map((s, i) => (
            <SourceCard key={`${s.document_id}-${i}`} source={s} />
          ))}
          {sources.length > 3 && (
            <button
              onClick={() => setShowAll((v) => !v)}
              className="text-xs font-medium text-brand hover:text-brand-dark"
            >
              {showAll ? 'Show less' : `Show all ${sources.length}`}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Message bubble ───────────────────────────────────────────────────────────

function MessageBubble({ msg }: { msg: LocalMessage }) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-brand px-4 py-3 text-sm text-white shadow-sm">
          {msg.content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] rounded-2xl rounded-tl-sm bg-white px-4 py-3 shadow-sm">
        <p className="whitespace-pre-wrap text-sm text-gray-800">{msg.content}</p>
        {msg.sources && msg.sources.length > 0 && (
          <SourcesSection sources={msg.sources} />
        )}
      </div>
    </div>
  )
}

// ─── Typing indicator ─────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm bg-white px-4 py-3 shadow-sm">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-2 w-2 rounded-full bg-gray-300"
            style={{ animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite` }}
          />
        ))}
        <style>{`
          @keyframes bounce {
            0%, 80%, 100% { transform: translateY(0); }
            40% { transform: translateY(-6px); }
          }
        `}</style>
      </div>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const [searchParams] = useSearchParams()

  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [activeConvId, setActiveConvId] = useState<string | undefined>(
    searchParams.get('conv') ?? undefined,
  )
  const [messages, setMessages] = useState<LocalMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loadingMessages, setLoadingMessages] = useState(false)

  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Load conversation list
  const loadConversations = useCallback(async () => {
    try {
      const list = await fetchConversations()
      setConversations(list)
    } catch {
      // Non-critical — just leave the list empty
    }
  }, [])

  useEffect(() => {
    void loadConversations()
  }, [loadConversations])

  // Load messages when active conversation changes
  useEffect(() => {
    if (!activeConvId) {
      setMessages([])
      return
    }
    setLoadingMessages(true)
    fetchMessages(activeConvId)
      .then((msgs: MessageResponse[]) => {
        setMessages(
          msgs.map((m) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            sources: m.sources,
          })),
        )
      })
      .catch(() => setError('Failed to load messages.'))
      .finally(() => setLoadingMessages(false))
  }, [activeConvId])

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  // Auto-resize textarea
  function handleInputChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 96)}px` // max ~4 rows
  }

  async function handleSend() {
    const question = input.trim()
    if (!question || sending) return

    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
    setError(null)

    // Optimistic user message
    const tempId = `local-${Date.now()}`
    setMessages((prev) => [
      ...prev,
      { id: tempId, role: 'user', content: question, sources: null },
    ])
    setSending(true)

    try {
      const res = await sendChat(question, activeConvId)
      setActiveConvId(res.conversation_id)
      setMessages((prev) => [
        ...prev,
        {
          id: `${res.conversation_id}-${Date.now()}`,
          role: 'assistant',
          content: res.answer,
          sources: res.sources,
        },
      ])
      await loadConversations()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message.')
      // Remove optimistic message on failure
      setMessages((prev) => prev.filter((m) => m.id !== tempId))
    } finally {
      setSending(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
  }

  function startNewChat() {
    setActiveConvId(undefined)
    setMessages([])
    setError(null)
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* ── Conversation list ── */}
      <div className="flex w-80 shrink-0 flex-col border-r border-gray-200 bg-white">
        <div className="border-b border-gray-100 p-4">
          <button
            onClick={startNewChat}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-dark"
          >
            <Plus size={16} />
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 ? (
            <p className="px-4 py-6 text-center text-sm text-gray-400">
              No conversations yet
            </p>
          ) : (
            conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => setActiveConvId(conv.id)}
                className={`w-full border-b border-gray-50 px-4 py-3 text-left transition-colors hover:bg-gray-50 ${
                  conv.id === activeConvId ? 'bg-brand-light' : ''
                }`}
              >
                <p
                  className={`truncate text-sm font-medium ${
                    conv.id === activeConvId ? 'text-brand' : 'text-gray-700'
                  }`}
                >
                  Conversation
                </p>
                <p className="mt-0.5 text-xs text-gray-400">
                  {formatDate(conv.created_at)}
                </p>
              </button>
            ))
          )}
        </div>
      </div>

      {/* ── Chat area ── */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {loadingMessages ? (
            <div className="flex justify-center pt-12">
              <Spinner size={28} className="text-brand" />
            </div>
          ) : messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-light">
                <span className="text-3xl">💬</span>
              </div>
              <p className="text-lg font-semibold text-gray-700">
                Ask anything
              </p>
              <p className="max-w-xs text-sm text-gray-400">
                Type a question below and let the assistant search your documents
                for the best answer.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} msg={msg} />
              ))}
              {sending && <TypingIndicator />}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Error banner */}
        {error && (
          <div className="mx-6 mb-2 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">
            {error}
            <button
              onClick={() => setError(null)}
              className="ml-2 font-medium underline"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Input bar */}
        <div className="border-t border-gray-200 bg-white px-6 py-4">
          <div className="flex items-end gap-3 rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 shadow-sm focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/20">
            <button
              type="button"
              className="shrink-0 text-gray-400 hover:text-gray-600"
              title="Attach file (coming soon)"
            >
              <Paperclip size={18} />
            </button>
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question… (Enter to send, Shift+Enter for new line)"
              className="flex-1 resize-none bg-transparent text-sm outline-none placeholder:text-gray-400"
            />
            <button
              onClick={() => void handleSend()}
              disabled={!input.trim() || sending}
              className="shrink-0 flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-white transition hover:bg-brand-dark disabled:opacity-40"
            >
              {sending ? <Spinner size={14} className="text-white" /> : <Send size={14} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
