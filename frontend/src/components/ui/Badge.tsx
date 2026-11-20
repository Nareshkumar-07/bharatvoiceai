import type { ReactNode } from 'react'
import { AlertTriangle, CheckCircle2, FlaskConical, Info, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

type Tone = 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'demo'

const tones: Record<Tone, string> = {
  neutral: 'border-white/10 bg-white/[0.05] text-ink-muted',
  success: 'border-emerald-400/25 bg-emerald-400/10 text-emerald-300',
  warning: 'border-amber-400/25 bg-amber-400/10 text-amber-300',
  danger: 'border-red-400/25 bg-red-400/10 text-red-300',
  info: 'border-accent/25 bg-accent/10 text-accent-light',
  demo: 'border-fuchsia-400/30 bg-fuchsia-400/10 text-fuchsia-300',
}

const icons = {
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: XCircle,
  info: Info,
  demo: FlaskConical,
  neutral: null,
} as const

export function Badge({
  children,
  tone = 'neutral',
  icon,
  className,
}: {
  children: ReactNode
  tone?: Tone
  icon?: boolean
  className?: string
}) {
  const Icon = icons[tone]
  return (
    <span className={cn('chip', tones[tone], className)}>
      {icon && Icon && <Icon className="h-3 w-3" />}
      {children}
    </span>
  )
}

export function EngineBadge({ status }: { status: string }) {
  if (status === 'demo_fixture')
    return (
      <Badge tone="demo" icon>
        Demo fixture
      </Badge>
    )
  if (status === 'degraded')
    return (
      <Badge tone="warning" icon>
        Fallback model
      </Badge>
    )
  if (status === 'unavailable')
    return (
      <Badge tone="danger" icon>
        Engine unavailable
      </Badge>
    )
  return (
    <Badge tone="success" icon>
      Live model
    </Badge>
  )
}

export function ConfidencePill({
  value,
  source,
}: {
  value: number | null | undefined
  source?: string | null
}) {
  if (value === null || value === undefined)
    return <Badge tone="neutral">Confidence not reported</Badge>
  const pct = Math.round(value * 100)
  const tone: Tone = pct >= 70 ? 'success' : pct >= 45 ? 'warning' : 'danger'
  const label = source === 'provider' ? 'model confidence' : source === 'proxy' ? 'proxy estimate' : 'confidence'
  return (
    <Badge tone={tone}>
      {pct}% {label}
    </Badge>
  )
}
