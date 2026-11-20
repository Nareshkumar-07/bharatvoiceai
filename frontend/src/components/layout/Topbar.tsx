import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Activity, ChevronDown, LogOut, Menu, Settings as SettingsIcon, Wifi, WifiOff } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { api } from '@/services/api'
import type { EngineStatusPayload } from '@/types'
import { Badge } from '@/components/ui/Badge'
import { cn } from '@/lib/utils'

export function Topbar({ onOpenSidebar }: { onOpenSidebar: () => void }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [status, setStatus] = useState<EngineStatusPayload | null>(null)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    let alive = true
    api
      .engineStatus()
      .then((s) => alive && setStatus(s))
      .catch(() => undefined)
    return () => {
      alive = false
    }
  }, [])

  const primary = status?.primary_engine
  const available = status?.primary_available

  return (
    <header className="sticky top-0 z-30 border-b border-white/[0.06] bg-canvas/70 backdrop-blur-xl">
      <div className="flex h-16 items-center gap-3 px-4 sm:px-6">
        <button
          className="rounded-lg p-2 text-ink-muted hover:bg-white/5 hover:text-ink lg:hidden"
          onClick={onOpenSidebar}
          aria-label="Open navigation"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="hidden items-center gap-2 sm:flex">
          {available ? (
            <Badge tone="success" icon>
              <Wifi className="h-3 w-3" /> {primary}
            </Badge>
          ) : (
            <Badge tone="warning" icon>
              <WifiOff className="h-3 w-3" /> {status ? 'no provider' : 'checking…'}
            </Badge>
          )}
          {status?.demo_mode && <Badge tone="demo">demo mode</Badge>}
          {status?.streaming_available && <Badge tone="info">streaming</Badge>}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <Link
            to="/app/analytics"
            className="hidden items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-ink-muted hover:bg-white/5 hover:text-ink sm:flex"
          >
            <Activity className="h-3.5 w-3.5" /> Usage
          </Link>

          <div className="relative">
            <button
              onClick={() => setMenuOpen((o) => !o)}
              className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-xs text-ink hover:border-white/20"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
            >
              <span className="grid h-6 w-6 place-items-center rounded-full bg-gradient-to-br from-primary to-accent text-[10px] font-semibold text-white">
                {(user?.full_name || user?.email || 'U').slice(0, 1).toUpperCase()}
              </span>
              <span className="hidden max-w-[10rem] truncate sm:block">{user?.full_name || user?.email}</span>
              <ChevronDown className={cn('h-3.5 w-3.5 text-ink-faint transition-transform', menuOpen && 'rotate-180')} />
            </button>
            {menuOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} aria-hidden />
                <div className="absolute right-0 z-20 mt-2 w-52 overflow-hidden rounded-xl border border-white/10 bg-canvas-700/95 p-1 shadow-2xl backdrop-blur-xl">
                  <div className="px-3 py-2">
                    <p className="truncate text-xs font-medium text-ink">{user?.full_name || 'Account'}</p>
                    <p className="truncate text-[11px] text-ink-faint">{user?.email}</p>
                  </div>
                  <div className="hairline my-1" />
                  <button
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-ink-muted hover:bg-white/5 hover:text-ink"
                    onClick={() => {
                      setMenuOpen(false)
                      navigate('/app/settings')
                    }}
                  >
                    <SettingsIcon className="h-3.5 w-3.5" /> Settings
                  </button>
                  <button
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-ink-muted hover:bg-white/5 hover:text-ink"
                    onClick={async () => {
                      setMenuOpen(false)
                      await logout()
                      navigate('/')
                    }}
                  >
                    <LogOut className="h-3.5 w-3.5" /> Sign out
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
