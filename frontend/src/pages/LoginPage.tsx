import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Lock, Eye, EyeOff } from 'lucide-react'
import { authLogin, authRegister } from '../api/client'
import { useAuth } from '../context/AuthContext'
import Spinner from '../components/Spinner'

type Tab = 'signin' | 'register'

export default function LoginPage() {
  const [tab, setTab] = useState<Tab>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()
  const { login } = useAuth()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      if (tab === 'signin') {
        await authLogin(email, password)
        login(email)
        navigate('/chat', { replace: true })
      } else {
        // Register then auto-login
        await authRegister(email, password)
        await authLogin(email, password)
        login(email)
        navigate('/chat', { replace: true })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-md overflow-hidden rounded-2xl shadow-lg">
        {/* Green gradient header */}
        <div className="flex flex-col items-center gap-3 bg-gradient-to-br from-brand to-brand-dark px-8 py-10 text-white">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-white/20 backdrop-blur">
            <Lock size={28} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">RAG Assistant</h1>
          <p className="text-sm text-white/80">
            Enterprise knowledge at your fingertips
          </p>
        </div>

        {/* Card body */}
        <div className="bg-white px-8 pb-8 pt-6">
          {/* Tabs */}
          <div className="mb-6 flex border-b border-gray-200">
            {(['signin', 'register'] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => {
                  setTab(t)
                  setError(null)
                }}
                className={`flex-1 pb-2 text-sm font-medium transition-colors ${
                  tab === t
                    ? 'border-b-2 border-brand text-brand'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {t === 'signin' ? 'Sign In' : 'Create Account'}
              </button>
            ))}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email */}
            <div>
              <label
                htmlFor="email"
                className="mb-1.5 block text-sm font-medium text-gray-700"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="w-full rounded-lg border border-gray-300 px-3.5 py-2.5 text-sm outline-none transition placeholder:text-gray-400 focus:border-brand focus:ring-2 focus:ring-brand/20"
              />
            </div>

            {/* Password */}
            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-sm font-medium text-gray-700"
              >
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPw ? 'text' : 'password'}
                  autoComplete={tab === 'signin' ? 'current-password' : 'new-password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-lg border border-gray-300 px-3.5 py-2.5 pr-10 text-sm outline-none transition placeholder:text-gray-400 focus:border-brand focus:ring-2 focus:ring-brand/20"
                />
                <button
                  type="button"
                  onClick={() => setShowPw((v) => !v)}
                  className="absolute inset-y-0 right-3 flex items-center text-gray-400 hover:text-gray-600"
                  tabIndex={-1}
                >
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
                {error}
              </p>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-dark disabled:opacity-60"
            >
              {loading && <Spinner size={16} className="text-white" />}
              {tab === 'signin' ? 'Sign In' : 'Create Account'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
