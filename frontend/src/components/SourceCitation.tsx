import React from 'react'
import { FileText, ExternalLink } from 'lucide-react'
import type { SourceResponse } from '../types'

interface SourceCitationProps {
  source: SourceResponse
  index?: number
  onClick?: () => void
}

export const SourceCitation: React.FC<SourceCitationProps> = ({
  source,
  index,
  onClick,
}) => {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Open excerpt: ${source.document}`}
      className="group inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50/60 px-2.5 py-1 text-xs text-emerald-800 transition hover:border-emerald-300 hover:bg-emerald-100 hover:shadow-xs focus:ring-2 focus:ring-emerald-500 focus:outline-hidden"
      title={`Open excerpt: ${source.document} (Page ${source.page})`}
    >
      <FileText className="h-3.5 w-3.5 text-emerald-600 group-hover:scale-110 transition-transform" />
      <span className="font-medium max-w-[140px] truncate">
        {source.document}
      </span>
      <span className="rounded-md bg-emerald-200/80 px-1 py-0.2 text-[10px] font-bold text-emerald-900">
        p.{source.page}
      </span>
      {index !== undefined && (
        <span className="text-[10px] text-emerald-600 font-mono">[{index + 1}]</span>
      )}
      <ExternalLink className="h-3 w-3 text-emerald-500 opacity-60 group-hover:opacity-100" />
    </button>
  )
}

export default SourceCitation
