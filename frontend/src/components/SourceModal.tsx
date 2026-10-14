import React, { useState } from 'react'
import { X, FileText, Copy, Check, Bookmark } from 'lucide-react'
import type { SourceResponse } from '../types'

interface SourceModalProps {
  source: SourceResponse | null
  onClose: () => void
}

export const SourceModal: React.FC<SourceModalProps> = ({ source, onClose }) => {
  const [copied, setCopied] = useState(false)

  if (!source) return null

  const handleCopy = () => {
    navigator.clipboard.writeText(source.text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const scorePct = Math.round(source.score * 100)

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-xl rounded-xl border border-slate-200 bg-white p-6 shadow-2xl animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-100 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-800 text-base leading-tight max-w-sm truncate" title={source.document}>
                {source.document}
              </h3>
              <div className="mt-1 flex items-center gap-2">
                <span className="inline-flex items-center gap-1 rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800">
                  <Bookmark className="h-3 w-3" /> Page {source.page}
                </span>
                <span className="text-xs text-slate-400">
                  Match Score: <span className="font-medium text-slate-600">{scorePct}%</span>
                </span>
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Passage */}
        <div className="my-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Verified Source Excerpt
            </span>
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-1 text-xs text-emerald-600 hover:text-emerald-700 font-medium transition"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5 text-emerald-600" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" />
                  Copy excerpt
                </>
              )}
            </button>
          </div>
          <div className="max-h-72 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50/70 p-4 font-sans text-sm leading-relaxed text-slate-700 select-text whitespace-pre-wrap">
            {source.text}
          </div>
        </div>

        {/* Relevance Bar */}
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
            <span>Retrieval Relevance</span>
            <span className="font-semibold text-emerald-700">{scorePct}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-emerald-500 transition-all duration-500"
              style={{ width: `${Math.min(scorePct, 100)}%` }}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="mt-5 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg bg-slate-800 px-4 py-2 text-xs font-medium text-white hover:bg-slate-900 transition shadow-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default SourceModal
