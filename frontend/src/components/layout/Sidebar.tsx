import { NavLink } from 'react-router-dom'
import {
  BarChart3,
  BookOpenText,
  BrainCircuit,
  LayoutDashboard,
  Languages,
  Mic,
  Settings,
  Sparkles,
  History as HistoryIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const NAV = [
  { to: '/app', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/app/workspace', label: 'Voice Workspace', icon: Mic },
  { to: '/app/history', label: 'History', icon: HistoryIcon },
  { to: '/app/vocabulary', label: 'My Vocabulary', icon: BookOpenText },
  { to: '/app/languages', label: 'Language Settings', icon: Languages },
  { to: '/app/intelligence', label: 'AI Intelligence', icon: BrainCircuit },
  { to: '/app/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/app/settings', label: 'Settings', icon: Settings },
]

export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="relative grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-primary to-accent shadow-glow-sm">
        <Sparkles className="h-4.5 w-4.5 text-white" style={{ height: 18, width: 18 }} />
      </span>
      {!compact && (
        <span className="leading-tight">
          <span className="block text-sm font-semibold tracking-tight text-ink">BharatVoice</span>
          <span className="block text-[10px] font-medium uppercase tracking-[0.18em] text-ink-faint">
            AI voice intelligence
          </span>
        </span>
      )}
    </div>
  )
}

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col gap-6 p-4">
      <NavLink to="/" className="px-2 pt-1" onClick={onNavigate}>
        <BrandMark />
      </NavLink>

      <nav className="flex-1 space-y-1" aria-label="Main navigation">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all',
                isActive
                  ? 'bg-gradient-to-r from-primary/20 to-accent/10 text-ink shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06)]'
                  : 'text-ink-muted hover:bg-white/[0.04] hover:text-ink',
              )
            }
          >
            {({ isActive }) => (
              <>
                <item.icon
                  className={cn('h-4 w-4 shrink-0', isActive ? 'text-primary-light' : 'text-ink-faint group-hover:text-ink-muted')}
                />
                <span className="truncate">{item.label}</span>
                {isActive && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-accent" />}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="rounded-xl border border-white/[0.07] bg-white/[0.02] p-3">
        <p className="text-[11px] font-medium uppercase tracking-wider text-ink-faint">Privacy</p>
        <p className="mt-1 text-[11px] leading-relaxed text-ink-muted">
          Audio is discarded after transcription unless you turn on retention in Settings.
        </p>
      </div>
    </div>
  )
}
