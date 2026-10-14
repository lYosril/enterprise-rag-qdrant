import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plus, Send, Zap, Sparkles, MessageSquare, AlertCircle } from 'lucide-react'
import {
  getConversations,
  getConversationMessages,
  sendQuestion,
  streamQuestion,
} from '../api/chat'
import type { ConversationSummary, MessageResponse, SourceResponse } from '../types'
import ChatMessage from '../components/ChatMessage'
import SourceModal from '../components/SourceModal'
import Spinner from '../components/Spinner'

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export const ChatPage: React.FC = () => {
  const [searchParams] = useSearchParams()
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [activeConvId, setActiveConvId] = useState<string | undefined>(
    searchParams.get('conv') ?? undefined,
  )
  const [messages, setMessages] = useState<MessageResponse[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [streamingEnabled, setStreamingEnabled] = useState(true)
  const [selectedSource, setSelectedSource] = useState<SourceResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loadingMessages, setLoadingMessages] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const loadConversations = useCallback(async () => {
    try {
      const data = await getConversations()
      setConversations(data)
    } catch {
      // Non-blocking
    }
  }, [])

  useEffect(() => {
    void loadConversations()
  }, [loadConversations])

  useEffect(() => {
    if (!activeConvId) {
      setMessages([])
      return
    }
    setLoadingMessages(true)
    getConversationMessages(activeConvId)
      .then((msgs) => setMessages(msgs))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Failed to load conversation messages'
        setError(msg)
      })
      .finally(() => setLoadingMessages(false))
  }, [activeConvId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`
  }

  const handleSend = async () => {
    const question = input.trim()
    if (!question || sending) return

    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
    setError(null)

    const tempUserMsg: MessageResponse = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: question,
      sources: null,
      created_at: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, tempUserMsg])
    setSending(true)

    if (streamingEnabled) {
      const tempAssistantId = `assistant-${Date.now()}`
      let accumulated = ''

      // Placeholder message for streaming tokens
      setMessages((prev) => [
        ...prev,
        {
          id: tempAssistantId,
          role: 'assistant',
          content: '',
          sources: null,
          created_at: new Date().toISOString(),
        },
      ])

      await streamQuestion({
        question,
        conversation_id: activeConvId,
        onToken: (token: string) => {
          accumulated += token
          setMessages((prev) =>
            prev.map((m) =>
              m.id === tempAssistantId ? { ...m, content: accumulated } : m,
            ),
          )
        },
        onSources: (sources: SourceResponse[], conversationId: string) => {
          setActiveConvId(conversationId)
          setMessages((prev) =>
            prev.map((m) =>
              m.id === tempAssistantId ? { ...m, sources } : m,
            ),
          )
        },
        onDone: () => {
          setSending(false)
          void loadConversations()
        },
        onError: (err: Error) => {
          setError(err.message)
          setSending(false)
          setMessages((prev) => prev.filter((m) => m.id !== tempAssistantId))
        },
      })
    } else {
      // Non-streaming fallback
      try {
        const res = await sendQuestion({
          question,
          conversation_id: activeConvId,
        })
        setActiveConvId(res.conversation_id)
        setMessages((prev) => [
          ...prev,
          {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: res.answer,
            sources: res.sources,
            created_at: new Date().toISOString(),
          },
        ])
        await loadConversations()
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to generate answer'
        setError(msg)
        setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id))
      } finally {
        setSending(false)
      }
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
  }

  const handleNewChat = () => {
    setActiveConvId(undefined)
    setMessages([])
    setError(null)
  }

  return (
    <div className="flex h-full overflow-hidden bg-slate-50">
      {/* ── Conversation Sidebar ── */}
      <div className="flex w-72 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="border-b border-slate-100 p-4">
          <button
            type="button"
            onClick={handleNewChat}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-xs font-semibold text-white shadow-xs transition hover:bg-emerald-700"
          >
            <Plus className="h-4 w-4" />
            New Conversation
          </button>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-slate-50">
          {conversations.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-400">
              <MessageSquare className="h-8 w-8 mx-auto text-slate-300 mb-2" />
              No conversation history yet. Start by asking a question!
            </div>
          ) : (
            conversations.map((conv) => (
              <button
                type="button"
                key={conv.id}
                onClick={() => setActiveConvId(conv.id)}
                className={`w-full px-4 py-3 text-left transition-colors flex items-start gap-2.5 ${
                  conv.id === activeConvId
                    ? 'bg-emerald-50/70 border-l-4 border-emerald-600'
                    : 'hover:bg-slate-50'
                }`}
              >
                <MessageSquare
                  className={`h-4 w-4 mt-0.5 shrink-0 ${
                    conv.id === activeConvId ? 'text-emerald-600' : 'text-slate-400'
                  }`}
                />
                <div className="overflow-hidden flex-1">
                  <p
                    className={`text-xs font-semibold truncate ${
                      conv.id === activeConvId ? 'text-emerald-900' : 'text-slate-700'
                    }`}
                  >
                    Conversation {conv.id.slice(0, 8)}
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    {formatDate(conv.created_at)}
                  </p>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* ── Main Chat Area ── */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Chat Header */}
        <div className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3.5">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-emerald-600" />
            <h2 className="text-sm font-bold text-slate-800">
              {activeConvId ? 'Grounded AI Chat' : 'New Q&A Session'}
            </h2>
          </div>

          {/* Streaming toggle */}
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1.5 cursor-pointer text-xs text-slate-600 font-medium">
              <Zap
                className={`h-3.5 w-3.5 ${
                  streamingEnabled ? 'text-amber-500 fill-amber-500' : 'text-slate-400'
                }`}
              />
              <span>Stream tokens</span>
              <input
                type="checkbox"
                checked={streamingEnabled}
                onChange={(e) => setStreamingEnabled(e.target.checked)}
                className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 h-3.5 w-3.5 ml-1"
              />
            </label>
          </div>
        </div>

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {loadingMessages ? (
            <div className="flex justify-center pt-20">
              <Spinner size={32} className="text-emerald-600" />
            </div>
          ) : messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-center max-w-md mx-auto">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-600 mb-4 shadow-xs">
                <Sparkles className="h-7 w-7" />
              </div>
              <h3 className="text-base font-bold text-slate-800">Enterprise Knowledge Search</h3>
              <p className="mt-1 text-xs text-slate-500 leading-relaxed">
                Ask any question about your organization policies, handbook, or uploaded documentation. Answers include verifiable citations from authorized source passages.
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {[
                  'What is our vacation and leave policy?',
                  'What are the requirements for computer monitoring?',
                  'How does the company handle policy conflicts?',
                ].map((sample) => (
                  <button
                    key={sample}
                    type="button"
                    onClick={() => {
                      setInput(sample)
                      textareaRef.current?.focus()
                    }}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 hover:border-emerald-300 hover:text-emerald-700 transition"
                  >
                    &ldquo;{sample}&rdquo;
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto space-y-4">
              {messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  onSelectSource={(src) => setSelectedSource(src)}
                />
              ))}
              {sending && !streamingEnabled && (
                <div className="flex items-center gap-2 text-xs text-slate-400 py-2">
                  <Spinner size={14} className="text-emerald-600" />
                  <span>Retrieving evidence and synthesizing answer...</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mx-6 mb-2 flex items-center justify-between rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-xs text-red-700 animate-in fade-in">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
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

        {/* Question Input Box */}
        <div className="border-t border-slate-200 bg-white p-4">
          <div className="max-w-4xl mx-auto flex items-end gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 focus-within:border-emerald-500 focus-within:bg-white focus-within:ring-2 focus-within:ring-emerald-500/20 transition-all">
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your documents… (Enter to send, Shift+Enter for newline)"
              className="flex-1 resize-none bg-transparent text-xs text-slate-800 placeholder:text-slate-400 focus:outline-hidden"
            />
            <button
              type="button"
              onClick={() => void handleSend()}
              disabled={!input.trim() || sending}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-emerald-600 text-white transition hover:bg-emerald-700 disabled:opacity-40 shadow-xs"
            >
              {sending ? <Spinner size={14} className="text-white" /> : <Send className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Source Citation Excerpt Modal */}
      <SourceModal
        source={selectedSource}
        onClose={() => setSelectedSource(null)}
      />
    </div>
  )
}

export default ChatPage
