import React from 'react'
import {
  MessageSquare,
  FileText,
  Activity,
  Clock,
  LogOut,
  Layers,
} from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

interface SidebarProps {
  className?: string
}

export const Sidebar: React.FC<SidebarProps> = ({ className = '' }) => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  const navItems = [
    { to: '/chat', label: 'RAG Assistant', icon: MessageSquare },
    { to: '/documents', label: 'Document Library', icon: FileText },
    { to: '/history', label: 'Chat History', icon: Clock },
    { to: '/settings', label: 'System & Metrics', icon: Activity },
  ]

  return (
    <aside
      className={`flex h-full w-64 shrink-0 flex-col border-r border-slate-200 bg-white select-none ${className}`}
    >
      {/* Brand Header */}
      <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-xs">
          <Layers className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-sm font-bold text-slate-800 tracking-tight leading-none">
            Enterprise RAG
          </h1>
          <span className="text-[11px] font-medium text-emerald-600">
            Assistant v2.0
          </span>
        </div>
      </div>

      {/* Nav List */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all ${
                isActive
                  ? 'bg-emerald-50 text-emerald-700 shadow-xs'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User Footer */}
      <div className="border-t border-slate-100 p-4">
        <div className="mb-3 px-2">
          <p className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
            Signed in as
          </p>
          <p
            className="truncate text-xs font-semibold text-slate-700 mt-0.5"
            title={user?.email}
          >
            {user?.email || 'authenticated user'}
          </p>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-slate-600 transition hover:bg-red-50 hover:text-red-700"
        >
          <LogOut className="h-4 w-4 text-slate-400 group-hover:text-red-600" />
          Sign out
        </button>
      </div>
    </aside>
  )
}

export default Sidebar
