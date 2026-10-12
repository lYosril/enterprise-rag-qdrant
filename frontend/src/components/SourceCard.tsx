import { useState } from 'react'
import { FileText } from 'lucide-react'
import type { SourceResponse } from '../api/client'

interface SourceCardProps {
  source: SourceResponse
}

export default function SourceCard({ source }: SourceCardProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="rounded-lg border border-gray-100 bg-white p-3 shadow-sm">
      {/* Header */}
      <div className="mb-2 flex items-center gap-2">
        <FileText size={14} className="shrink-0 text-gray-400" />
        <span
          className="flex-1 truncate text-xs font-medium text-gray-700"
          title={source.document}
        >
          {source.document}
        </span>
        <span className="shrink-0 rounded-full bg-brand-light px-2 py-0.5 text-xs font-semibold text-brand-dark">
          p.&nbsp;{source.page}
        </span>
      </div>

      {/* Passage */}
      <p
        className={`text-xs text-gray-600 ${expanded ? '' : 'line-clamp-3'}`}
      >
        {source.text}
      </p>
      {source.text.length > 180 && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="mt-1 text-xs font-medium text-brand hover:text-brand-dark"
        >
          {expanded ? 'Collapse' : 'Expand'}
        </button>
      )}

      {/* Relevance bar */}
      <div className="mt-2">
        <div className="mb-0.5 flex items-center justify-between">
          <span className="text-[10px] text-gray-400">Relevance</span>
          <span className="text-[10px] text-gray-500">
            {Math.round(source.score * 100)}%
          </span>
        </div>
        <div className="h-1 w-full overflow-hidden rounded-full bg-gray-100">
          <div
            className="h-full rounded-full bg-brand transition-all"
            style={{ width: `${Math.min(source.score * 100, 100)}%` }}
          />
        </div>
      </div>
    </div>
  )
}
