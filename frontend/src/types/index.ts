export type DocumentStatus = 'uploaded' | 'processing' | 'indexed' | 'failed' | 'deleting'

export interface DocumentResponse {
  id: string
  filename: string
  status: DocumentStatus
  chunk_count: number
  created_at: string
  error_message?: string | null
}

export interface SourceResponse {
  document_id: string
  document: string
  page: number
  text: string
  score: number
}

export interface ChatResponse {
  conversation_id: string
  answer: string
  sources: SourceResponse[]
  agent_trace?: Array<{
    attempt: number
    query: string
    was_rewritten: boolean
    source_count: number
    source_ids: string[]
  }>
}

export interface ConversationSummary {
  id: string
  created_at: string
}

export interface MessageResponse {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources: SourceResponse[] | null
  created_at: string
}

export interface IngestionStats {
  total_documents: number
  total_chunks: number
  status_counts: Record<string, number>
  user_documents: number
}

export interface MonitoringStats {
  status: string
  ingestion: IngestionStats
  conversations: {
    total_conversations: number
    total_messages: number
  }
  services: Record<string, { status: string; latency_ms?: number; model?: string }>
  evaluation: {
    recall_at_5: number
    mrr: number
    fact_coverage: number
    abstention_accuracy: number
    citation_precision: number
    avg_answer_latency_sec: number
  }
  llm_usage: {
    total_prompt_tokens: number
    total_completion_tokens: number
    estimated_cost_usd: number
  }
}
