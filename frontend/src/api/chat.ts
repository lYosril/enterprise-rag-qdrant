import { api, getToken } from './client'
import type { ChatResponse, ConversationSummary, MessageResponse, SourceResponse } from '../types'

export interface ChatRequest {
  question: string
  conversation_id?: string
}

export async function sendQuestion(payload: ChatRequest): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>('/api/v1/chat', payload)
  return response.data
}

export async function getConversations(): Promise<ConversationSummary[]> {
  const response = await api.get<ConversationSummary[]>('/api/v1/conversations')
  return response.data
}

export async function getConversationMessages(conversationId: string): Promise<MessageResponse[]> {
  const response = await api.get<MessageResponse[]>(
    `/api/v1/conversations/${conversationId}/messages`,
  )
  return response.data
}

export async function streamQuestion({
  question,
  conversation_id,
  onToken,
  onSources,
  onDone,
  onError,
}: {
  question: string
  conversation_id?: string
  onToken: (token: string) => void
  onSources: (sources: SourceResponse[], conversationId: string) => void
  onDone: () => void
  onError: (err: Error) => void
}): Promise<void> {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  const token = getToken()

  try {
    const response = await fetch(`${baseUrl}/api/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        question,
        ...(conversation_id ? { conversation_id } : {}),
      }),
    })

    if (!response.ok) {
      let detail = `Streaming failed with status ${response.status}`
      try {
        const errJson = await response.json()
        if (errJson.detail) detail = errJson.detail
      } catch {
        // use default
      }
      throw new Error(detail)
    }

    if (!response.body) {
      throw new Error('ReadableStream not supported by browser.')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const block of lines) {
        const trimmed = block.trim()
        if (!trimmed.startsWith('data:')) continue
        const dataStr = trimmed.replace(/^data:\s*/, '')

        if (dataStr === '[DONE]') {
          onDone()
          return
        }

        try {
          const parsed = JSON.parse(dataStr)
          if (parsed.type === 'token') {
            onToken(parsed.token)
          } else if (parsed.type === 'sources') {
            onSources(parsed.sources || [], parsed.conversation_id)
          }
        } catch {
          // ignore malformed SSE chunk
        }
      }
    }
    onDone()
  } catch (err: unknown) {
    onError(err instanceof Error ? err : new Error(String(err)))
  }
}
