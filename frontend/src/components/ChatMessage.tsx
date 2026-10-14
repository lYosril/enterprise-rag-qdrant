import React, { useState } from 'react'
import { Copy, Check, Bot, User, Sparkles, AlertCircle } from 'lucide-react'
import { SourceCitation } from './SourceCitation'
import type { MessageResponse, SourceResponse } from '../types'

interface ChatMessageProps {
  message: MessageResponse
  onSelectSource?: (source: SourceResponse) => void
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message, onSelectSource }) => {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Check if answer is an abstention response
  const isAbstention =
    !isUser &&
    (message.content.toLowerCase().includes("couldn't find") ||
      message.content.toLowerCase().includes('not find relevant') ||
      message.content.toLowerCase().includes('insufficient evidence') ||
      message.content.toLowerCase().includes('no relevant'))

  if (isUser) {
    return (
      <div className="flex justify-end mb-4 animate-in fade-in duration-200">
        <div className="flex max-w-2xl items-start gap-3 flex-row-reverse">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-white shadow-xs">
            <User className="h-4 w-4" />
          </div>
          <div className="rounded-2xl rounded-tr-xs bg-emerald-600 px-4 py-2.5 text-white shadow-xs text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start mb-6 animate-in fade-in duration-200">
      <div className="flex max-w-3xl items-start gap-3 w-full">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 shadow-xs border border-emerald-200">
          <Bot className="h-4 w-4" />
        </div>

        <div className="flex-1 rounded-2xl rounded-tl-xs border border-slate-200 bg-white p-4 shadow-xs">
          {/* Header bar */}
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-800">
              <Sparkles className="h-3.5 w-3.5 text-emerald-500" />
              <span>Grounded Answer</span>
            </div>
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-700 transition"
              title="Copy answer"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5 text-emerald-600" />
                  <span className="text-emerald-600 font-medium">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>

          {/* Abstention Callout */}
          {isAbstention && (
            <div className="mb-3 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-800">
              <AlertCircle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
              <div>
                <span className="font-semibold">Notice:</span> Insufficient information in authorized documents to guarantee an authoritative answer.
              </div>
            </div>
          )}

          {/* Answer Text */}
          <div className="prose prose-sm max-w-none text-slate-800 leading-relaxed whitespace-pre-wrap font-sans text-sm">
            {message.content}
          </div>

          {/* Source Citations */}
          {message.sources && message.sources.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-100">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                Verified Sources ({message.sources.length})
              </div>
              <div className="flex flex-wrap gap-2">
                {message.sources.map((source, idx) => (
                  <SourceCitation
                    key={`${source.document_id || source.document}-${source.page}-${idx}`}
                    source={source}
                    index={idx}
                    onClick={() => onSelectSource?.(source)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ChatMessage
