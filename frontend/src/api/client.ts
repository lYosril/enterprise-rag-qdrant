import axios from 'axios'
export type { DocumentResponse, SourceResponse, ChatResponse, ConversationSummary, MessageResponse } from '../types'
export { registerUser as authRegister, loginUser as authLogin, logoutUser as authLogout } from './auth'
export { getDocuments as fetchDocuments, uploadDocument, deleteDocument } from './documents'
export { sendQuestion as sendChat, getConversations as fetchConversations, getConversationMessages as fetchMessages } from './chat'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 60000,
})

const TOKEN_KEY = 'access_token'

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY) || sessionStorage.getItem('rag_token')
}

export function setToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token)
  sessionStorage.setItem('rag_token', token)
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem('rag_token')
}

api.interceptors.request.use((config) => {
  const token = getToken()

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearToken()
      window.dispatchEvent(new Event('auth:logout'))
    }
    return Promise.reject(error)
  },
)
