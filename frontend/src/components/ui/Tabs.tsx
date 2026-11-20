import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export interface TabItem {
  id: string
  label: string
  icon?: ReactNode
  badge?: ReactNode
}

export function Tabs({
  items,
  value,
  onChange,
  size = 'md',
  className,
}: {
  items: TabItem[]
  value: string
  onChange: (id: string) => void
  size?: 'sm' | 'md'
  className?: string
}) {
  return (
    <div role="tablist" className={cn('flex flex-wrap gap-1 rounded-xl border border-white/[0.07] bg-black/25 p-1', className)}>
      {items.map((item) => {
        const active = item.id === value
        return (
          <button
            key={item.id}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(item.id)}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-lg font-medium transition-all',
              size === 'sm' ? 'px-2.5 py-1.5 text-[11px]' : 'px-3.5 py-2 text-xs',
              active
                ? 'bg-gradient-to-r from-primary/25 to-accent/15 text-ink shadow-[inset_0_1px_0_0_rgba(255,255,255,0.08)]'
                : 'text-ink-muted hover:bg-white/[0.04] hover:text-ink',
            )}
          >
            {item.icon}
            {item.label}
            {item.badge}
          </button>
        )
      })}
    </div>
  )
}
