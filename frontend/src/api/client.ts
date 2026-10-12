// ─── Types ───────────────────────────────────────────────────────────────────

export interface DocumentResponse {
  id: string
  filename: string
  status: 'uploaded' | 'processing' | 'indexed' | 'failed'
  chunk_count: number
  created_at: string
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

// ─── Token helpers ────────────────────────────────────────────────────────────

const TOKEN_KEY = 'rag_token'

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY)
}

// ─── Core fetch helper ────────────────────────────────────────────────────────

export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const token = getToken()
  const headers = new Headers(init.headers as HeadersInit | undefined)

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`/api${path}`, { ...init, headers })

  if (response.status === 401) {
    clearToken()
    window.dispatchEvent(new Event('auth:logout'))
    throw new Error('Session expired. Please log in again.')
  }

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) {
        detail = typeof body.detail === 'string'
          ? body.detail
          : JSON.stringify(body.detail)
      }
    } catch {
      // body wasn't JSON — keep the generic message
    }
    throw new Error(detail)
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as unknown as T
  }

  return response.json() as Promise<T>
}

// ─── Auth API ─────────────────────────────────────────────────────────────────

export async function authRegister(
  email: string,
  password: string,
): Promise<{ id: string; email: string }> {
  return apiFetch<{ id: string; email: string }>('/v1/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
}

export async function authLogin(
  email: string,
  password: string,
): Promise<{ access_token: string }> {
  const body = new URLSearchParams()
  body.set('username', email)
  body.set('password', password)

  const result = await apiFetch<{ access_token: string; token_type: string }>(
    '/v1/auth/token',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    },
  )

  setToken(result.access_token)
  return { access_token: result.access_token }
}

export function authLogout(): void {
  clearToken()
}

// ─── Documents API ────────────────────────────────────────────────────────────

export function fetchDocuments(): Promise<DocumentResponse[]> {
  return apiFetch<DocumentResponse[]>('/v1/documents')
}

export function uploadDocument(file: File): Promise<DocumentResponse> {
  const form = new FormData()
  form.append('file', file)
  return apiFetch<DocumentResponse>('/v1/documents/upload', {
    method: 'POST',
    body: form,
  })
}

export async function deleteDocument(id: string): Promise<void> {
  await apiFetch<{ message: string }>(`/v1/documents/${id}`, {
    method: 'DELETE',
  })
}

// ─── Conversations API ────────────────────────────────────────────────────────

export function fetchConversations(): Promise<ConversationSummary[]> {
  return apiFetch<ConversationSummary[]>('/v1/conversations')
}

export function fetchMessages(conversationId: string): Promise<MessageResponse[]> {
  return apiFetch<MessageResponse[]>(`/v1/conversations/${conversationId}/messages`)
}

// ─── Chat API ─────────────────────────────────────────────────────────────────

export function sendChat(
  question: string,
  conversationId?: string,
): Promise<ChatResponse> {
  return apiFetch<ChatResponse>('/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      ...(conversationId ? { conversation_id: conversationId } : {}),
    }),
  })
}
