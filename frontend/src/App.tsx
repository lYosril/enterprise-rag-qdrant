import { useEffect } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { getToken } from './api/client'
import AppShell from './components/AppShell'
import LoginPage from './pages/LoginPage'
import ChatPage from './pages/ChatPage'
import DocumentsPage from './pages/DocumentsPage'
import HistoryPage from './pages/HistoryPage'

// ─── Protected route wrapper ──────────────────────────────────────────────────

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand border-t-transparent" />
      </div>
    )
  }

  if (!getToken()) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

// ─── Inner app (has access to navigate) ──────────────────────────────────────

function InnerApp() {
  const navigate = useNavigate()
  const { logout } = useAuth()

  useEffect(() => {
    function handleLogout() {
      logout()
      navigate('/login', { replace: true })
    }
    window.addEventListener('auth:logout', handleLogout)
    return () => window.removeEventListener('auth:logout', handleLogout)
  }, [navigate, logout])

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      {/* Root redirect */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Navigate to="/chat" replace />
          </ProtectedRoute>
        }
      />

      {/* Protected shell routes */}
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/history" element={<HistoryPage />} />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

// ─── App root ─────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <AuthProvider>
      <InnerApp />
    </AuthProvider>
  )
}
