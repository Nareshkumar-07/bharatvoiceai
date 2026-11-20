import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/lib/utils'

export function Card({ className, children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('glass p-5', className)} {...rest}>
      {children}
    </div>
  )
}

export function CardHeader({
  title,
  description,
  action,
  icon,
}: {
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
  icon?: ReactNode
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-4">
      <div className="flex items-start gap-3">
        {icon && (
          <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-white/10 bg-white/[0.04] text-primary-light">
            {icon}
          </span>
        )}
        <div>
          <h3 className="text-sm font-semibold text-ink">{title}</h3>
          {description && <p className="mt-1 text-xs leading-relaxed text-ink-muted">{description}</p>}
        </div>
      </div>
      {action}
    </div>
  )
}

export function StatCard({
  label,
  value,
  hint,
  icon,
  tone = 'primary',
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  icon?: ReactNode
  tone?: 'primary' | 'accent' | 'success' | 'muted'
}) {
  const tones = {
    primary: 'text-primary-light border-primary/20 bg-primary/10',
    accent: 'text-accent-light border-accent/20 bg-accent/10',
    success: 'text-emerald-300 border-emerald-400/20 bg-emerald-400/10',
    muted: 'text-ink-muted border-white/10 bg-white/[0.04]',
  } as const
  return (
    <Card className="card-hover">
      <div className="flex items-start justify-between">
        <p className="text-xs font-medium uppercase tracking-wider text-ink-faint">{label}</p>
        {icon && <span className={cn('grid h-8 w-8 place-items-center rounded-lg border', tones[tone])}>{icon}</span>}
      </div>
      <p className="mt-3 text-2xl font-semibold tracking-tight text-ink">{value}</p>
      {hint && <p className="mt-1.5 text-xs text-ink-faint">{hint}</p>}
    </Card>
  )
}
