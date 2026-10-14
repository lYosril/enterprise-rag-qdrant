import { api } from './client'
import type { DocumentResponse } from '../types'

export async function uploadDocument(file: File): Promise<DocumentResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post<DocumentResponse>(
    '/api/v1/documents/upload',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    },
  )

  return response.data
}

export async function getDocuments(): Promise<DocumentResponse[]> {
  const response = await api.get<DocumentResponse[]>('/api/v1/documents')
  return response.data
}

export async function deleteDocument(documentId: string): Promise<void> {
  await api.delete(`/api/v1/documents/${documentId}`)
}

export async function retryDocument(documentId: string): Promise<DocumentResponse> {
  const response = await api.post<DocumentResponse>(
    `/api/v1/documents/${documentId}/retry`,
  )
  return response.data
}

export async function reconcileDocuments(): Promise<unknown> {
  const response = await api.post('/api/v1/documents/reconcile')
  return response.data
}
