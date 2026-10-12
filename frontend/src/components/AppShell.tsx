import { Clock, FileText, Globe, LogOut, MessageSquare } from 'lucide-react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS = [
  { to: '/chat', label: 'Chat', Icon: MessageSquare },
  { to: '/documents', label: 'Documents', Icon: FileText },
  { to: '/history', label: 'History', Icon: Clock },
]

export default function AppShell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* ── Sidebar ── */}
      <aside className="flex h-full w-64 shrink-0 flex-col border-r border-gray-200 bg-white">
        {/* Logo */}
        <div className="flex items-center gap-2.5 border-b border-gray-100 px-5 py-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand">
            <Globe size={18} className="text-white" />
          </div>
          <span className="text-base font-bold text-gray-900 tracking-tight">
            RAG Assistant
          </span>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {NAV_ITEMS.map(({ to, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                  isActive
                    ? 'bg-brand-light font-semibold text-brand'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer: user + logout */}
        <div className="border-t border-gray-100 px-4 py-4">
          <p
            className="mb-2 truncate text-xs text-gray-500"
            title={user?.email}
          >
            {user?.email ?? 'user'}
          </p>
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-600 transition-colors hover:bg-red-50 hover:text-red-600"
          >
            <LogOut size={16} />
            Sign out
          </button>
        </div>
      </aside>

      {/* ── Main content ── */}
      <main className="flex flex-1 flex-col overflow-hidden bg-gray-50">
        <Outlet />
      </main>
    </div>
  )
}
