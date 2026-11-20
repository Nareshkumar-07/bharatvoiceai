import { AlertTriangle } from 'lucide-react'
import type { Segment } from '@/types'
import { languageName, percent } from '@/lib/utils'
import { cn } from '@/lib/utils'

const LANGUAGE_COLORS: Record<string, string> = {
  'ta-IN': 'border-primary/40 bg-primary/10 text-primary-light',
  'hi-IN': 'border-amber-400/40 bg-amber-400/10 text-amber-200',
  'te-IN': 'border-emerald-400/40 bg-emerald-400/10 text-emerald-200',
  'ml-IN': 'border-sky-400/40 bg-sky-400/10 text-sky-200',
  'kn-IN': 'border-rose-400/40 bg-rose-400/10 text-rose-200',
  'bn-IN': 'border-violet-400/40 bg-violet-400/10 text-violet-200',
  'en-IN': 'border-accent/40 bg-accent/10 text-accent-light',
}

export function TranscriptView({ segments }: { segments: Segment[] }) {
  if (!segments.length) return null
  return (
    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-2">
      {segments.map((segment, index) => {
        const color = LANGUAGE_COLORS[segment.language ?? ''] ?? 'border-white/15 bg-white/[0.05] text-ink'
        return (
          <span
            key={`${segment.text}-${index}`}
            className={cn(
              'group relative inline-flex flex-col rounded-lg border px-2 py-1 text-sm leading-relaxed',
              color,
              segment.is_uncertain && 'border-dashed',
            )}
            title={
              segment.is_uncertain
                ? 'Uncertain: the language of this span could not be attributed confidently'
                : `${languageName(segment.language)}${
                    segment.confidence !== null && segment.confidence !== undefined
                      ? ` · ${percent(segment.confidence)} heuristic`
                      : ''
                  }`
            }
          >
            <span className={segment.is_uncertain ? 'opacity-70' : undefined}>{segment.text}</span>
            <span className="mt-0.5 flex items-center gap-1 text-[9px] uppercase tracking-wider opacity-70">
              {segment.is_uncertain && <AlertTriangle className="h-2.5 w-2.5" />}
              {segment.is_uncertain ? 'uncertain' : segment.language_name ?? languageName(segment.language)}
            </span>
          </span>
        )
      })}
    </div>
  )
}

export function SegmentLegend({ segments }: { segments: Segment[] }) {
  const used = Array.from(new Set(segments.map((s) => s.language).filter(Boolean) as string[]))
  if (!used.length) return null
  return (
    <div className="flex flex-wrap items-center gap-2">
      {used.map((code) => (
        <span
          key={code}
          className={cn('chip', LANGUAGE_COLORS[code] ?? 'border-white/15 bg-white/[0.05]')}
        >
          {languageName(code)}
        </span>
      ))}
      {segments.some((s) => s.is_uncertain) && (
        <span className="chip border-dashed border-white/20 text-ink-faint">uncertain span</span>
      )}
    </div>
  )
}
