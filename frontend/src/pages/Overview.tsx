import { Link } from 'react-router-dom'
import {
  ArrowRight,
  BarChart3,
  BookOpenText,
  BrainCircuit,
  Clock,
  FileText,
  Mic,
  Sparkles,
  TrendingUp,
  Type,
} from 'lucide-react'
import { useApiResource } from '@/hooks/useApiResource'
import { api } from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import { Card, CardHeader, StatCard } from '@/components/ui/Card'
import { Badge, EngineBadge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { EmptyState, ErrorState, SkeletonRows } from '@/components/ui/States'
import { formatDuration, formatRelative, greeting, languageName } from '@/lib/utils'

export default function Overview() {
  const { user } = useAuth()
  const overview = useApiResource(() => api.overview(), [])
  const history = useApiResource(() => api.history({ page: 1, page_size: 5 }), [])
  const engine = useApiResource(() => api.engineStatus(), [])

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">
            {greeting()}, {user?.full_name?.split(' ')[0] || 'there'}
          </h1>
          <p className="mt-1 text-sm text-ink-muted">Here is what your voice has been doing.</p>
        </div>
        <Link to="/app/workspace">
          <Button icon={<Mic className="h-4 w-4" />} iconRight={<ArrowRight className="h-4 w-4" />}>
            Open workspace
          </Button>
        </Link>
      </div>

      {engine.data && !engine.data.primary_available && (
        <div className="glass flex flex-wrap items-center gap-3 border-amber-400/20 bg-amber-400/[0.06] p-4">
          <Badge tone="warning" icon>
            No speech provider
          </Badge>
          <p className="flex-1 text-xs text-amber-100/90">
            {engine.data.primary_unavailable_reason ??
              'Set SARVAM_API_KEY on the backend to enable real recognition.'}
          </p>
          <Link to="/app/intelligence" className="text-xs font-medium text-amber-200 hover:underline">
            See engine status
          </Link>
        </div>
      )}

      {overview.error && <ErrorState message={overview.error} onRetry={overview.reload} />}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Words transcribed"
          value={overview.data?.total_words.toLocaleString('en-IN') ?? '—'}
          hint={`${overview.data?.words_this_week ?? 0} this week`}
          icon={<Type className="h-4 w-4" />}
        />
        <StatCard
          label="Recordings"
          value={overview.data?.total_transcriptions ?? '—'}
          hint={`${formatDuration(overview.data?.total_duration_seconds ?? 0)} of audio`}
          icon={<Mic className="h-4 w-4" />}
          tone="accent"
        />
        <StatCard
          label="Code-mixed speech"
          value={`${overview.data?.code_mixed_percentage ?? 0}%`}
          hint="of your recordings switch language"
          icon={<TrendingUp className="h-4 w-4" />}
          tone="success"
        />
        <StatCard
          label="Day streak"
          value={overview.data?.current_streak_days ?? 0}
          hint={`${overview.data?.languages_used ?? 0} languages used`}
          icon={<Sparkles className="h-4 w-4" />}
          tone="muted"
        />
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader
            title="Recent transcriptions"
            description="Stored on this server. Audio is discarded unless you opted in."
            icon={<FileText className="h-4 w-4" />}
            action={
              <Link to="/app/history" className="text-xs text-ink-muted hover:text-ink">
                View all
              </Link>
            }
          />
          {history.loading ? (
            <SkeletonRows rows={3} />
          ) : history.data && history.data.items.length > 0 ? (
            <ul className="space-y-2">
              {history.data.items.map((item) => (
                <li key={item.id}>
                  <Link
                    to={`/app/history?open=${item.id}`}
                    className="flex items-start gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 transition-colors hover:border-primary/25 hover:bg-white/[0.04]"
                  >
                    <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-white/10 bg-white/[0.04] text-primary-light">
                      <Mic className="h-3.5 w-3.5" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-ink">{item.title}</p>
                      <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-ink-faint">
                        <Clock className="h-3 w-3" /> {formatRelative(item.created_at)}
                        <span>·</span>
                        {formatDuration(item.duration_seconds)}
                        <span>·</span>
                        {item.detected_languages.map(languageName).join(', ') || 'unknown language'}
                      </p>
                    </div>
                    <EngineBadge status={item.engine_status} />
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              icon={<Mic className="h-5 w-5" />}
              title="No recordings yet"
              description="Your first dictation will show up here with its language mix and engine status."
              action={
                <Link to="/app/workspace">
                  <Button size="sm">Record now</Button>
                </Link>
              }
            />
          )}
        </Card>

        <div className="space-y-5">
          <Card>
            <CardHeader title="Quick actions" icon={<Sparkles className="h-4 w-4" />} />
            <div className="space-y-2">
              {[
                { to: '/app/vocabulary', label: 'Add a name or term', icon: BookOpenText, hint: 'Improves recognition of your words' },
                { to: '/app/intelligence', label: 'Inspect the router', icon: BrainCircuit, hint: 'See routing decisions and calibration' },
                { to: '/app/analytics', label: 'Read analytics', icon: BarChart3, hint: 'Languages, latency, model usage' },
              ].map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  className="flex items-center gap-3 rounded-xl border border-white/[0.06] p-3 transition-colors hover:border-primary/25 hover:bg-white/[0.03]"
                >
                  <item.icon className="h-4 w-4 text-primary-light" />
                  <span className="min-w-0 flex-1">
                    <span className="block text-xs font-medium text-ink">{item.label}</span>
                    <span className="block text-[11px] text-ink-faint">{item.hint}</span>
                  </span>
                  <ArrowRight className="h-3.5 w-3.5 text-ink-faint" />
                </Link>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader title="Engine" description="What is answering your requests right now." icon={<BrainCircuit className="h-4 w-4" />} />
            {engine.loading ? (
              <p className="text-xs text-ink-faint">Checking…</p>
            ) : engine.data ? (
              <div className="space-y-2">
                {engine.data.models.map((m) => (
                  <div key={m.model_id} className="flex items-center justify-between gap-2 text-xs">
                    <span className="flex items-center gap-2">
                      <span
                        className={
                          m.available
                            ? 'h-1.5 w-1.5 rounded-full bg-emerald-400'
                            : 'h-1.5 w-1.5 rounded-full bg-white/25'
                        }
                      />
                      <span className={m.available ? 'text-ink' : 'text-ink-faint'}>{m.model_id}</span>
                      {m.is_primary && <Badge tone="info">primary</Badge>}
                    </span>
                    <span className="font-mono text-[10px] text-ink-faint">{m.runtime}</span>
                  </div>
                ))}
                <p className="pt-2 text-[11px] leading-relaxed text-ink-faint">{engine.data.notes[0]}</p>
              </div>
            ) : (
              <p className="text-xs text-ink-faint">Engine status unavailable.</p>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
