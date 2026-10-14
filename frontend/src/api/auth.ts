import { api, setToken, clearToken } from './client'

export interface UserResponse {
  id: string
  email: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export async function registerUser(email: string, password: string): Promise<UserResponse> {
  const response = await api.post<UserResponse>('/api/v1/auth/register', {
    email,
    password,
  })
  return response.data
}

export async function loginUser(email: string, password: string): Promise<TokenResponse> {
  const formData = new URLSearchParams()
  formData.append('username', email)
  formData.append('password', password)

  const response = await api.post<TokenResponse>('/api/v1/auth/token', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  })

  if (response.data.access_token) {
    setToken(response.data.access_token)
  }

  return response.data
}

export function logoutUser(): void {
  clearToken()
}
