import { useState } from 'react'
import { Activity, Clock, Gauge, Languages as LanguagesIcon, Mic, Type, TrendingUp } from 'lucide-react'
import { useApiResource } from '@/hooks/useApiResource'
import { api } from '@/services/api'
import { Card, CardHeader, StatCard } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Tabs } from '@/components/ui/Tabs'
import { ErrorState, LoadingState } from '@/components/ui/States'
import { ActivityAreaChart, LanguagePieChart, ModelBarChart } from '@/charts/Charts'
import { formatDuration, percent } from '@/lib/utils'

export default function Analytics() {
  const overview = useApiResource(() => api.overview(), [])
  const languages = useApiResource(() => api.languageUsage(), [])
  const performance = useApiResource(() => api.performance(), [])
  const [granularity, setGranularity] = useState<'day' | 'week'>('day')
  const activity = useApiResource(() => api.activity(granularity), [granularity])

  const loading = overview.loading || languages.loading || performance.loading

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Analytics</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Computed from your stored transcriptions. Nothing here is estimated or back-filled.
          </p>
        </div>
        {overview.data && !overview.data.has_data && <Badge tone="neutral">no data yet</Badge>}
      </div>

      {overview.error && <ErrorState message={overview.error} onRetry={overview.reload} />}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total words"
          value={(overview.data?.total_words ?? 0).toLocaleString('en-IN')}
          hint={`${overview.data?.words_this_week ?? 0} this week`}
          icon={<Type className="h-4 w-4" />}
        />
        <StatCard
          label="Recording time"
          value={formatDuration(overview.data?.total_duration_seconds ?? 0)}
          hint={`${overview.data?.total_transcriptions ?? 0} recordings`}
          icon={<Clock className="h-4 w-4" />}
          tone="accent"
        />
        <StatCard
          label="Code-mixed"
          value={`${overview.data?.code_mixed_percentage ?? 0}%`}
          hint="share of recordings"
          icon={<TrendingUp className="h-4 w-4" />}
          tone="success"
        />
        <StatCard
          label="Correction rate"
          value={
            overview.data?.average_correction_rate !== null && overview.data?.average_correction_rate !== undefined
              ? percent(overview.data.average_correction_rate, 2)
              : '—'
          }
          hint="corrections per word"
          icon={<Activity className="h-4 w-4" />}
          tone="muted"
        />
      </div>

      <Card>
        <CardHeader
          title="Transcription activity"
          description="Words transcribed per period, from stored rows only."
          icon={<Mic className="h-4 w-4" />}
          action={
            <Tabs
              size="sm"
              items={[
                { id: 'day', label: 'Daily' },
                { id: 'week', label: 'Weekly' },
              ]}
              value={granularity}
              onChange={(v) => setGranularity(v as 'day' | 'week')}
            />
          }
        />
        {activity.loading ? <LoadingState /> : <ActivityAreaChart data={activity.data ?? []} />}
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader title="Language mix" description="Detected languages across your recordings." icon={<LanguagesIcon className="h-4 w-4" />} />
          {loading ? <LoadingState /> : <LanguagePieChart data={languages.data ?? []} />}
        </Card>

        <Card>
          <CardHeader title="Recognition model usage" description="Which engine produced each transcript." icon={<Gauge className="h-4 w-4" />} />
          {loading ? (
            <LoadingState />
          ) : (
            <ModelBarChart
              data={Object.entries(performance.data?.model_usage ?? {}).map(([name, count]) => ({ name, count }))}
            />
          )}
        </Card>
      </div>

      <Card>
        <CardHeader title="Performance" description="Latency and confidence coverage as actually recorded." icon={<Gauge className="h-4 w-4" />} />
        <div className="grid gap-3 sm:grid-cols-3">
          <StatCard
            label="Average latency"
            value={performance.data?.average_latency_ms ? `${Math.round(performance.data.average_latency_ms)} ms` : '—'}
            tone="primary"
          />
          <StatCard
            label="p95 latency"
            value={performance.data?.p95_latency_ms ? `${Math.round(performance.data.p95_latency_ms)} ms` : '—'}
            tone="accent"
          />
          <StatCard
            label="Confidence coverage"
            value={percent(performance.data?.confidence_coverage ?? 0)}
            hint="transcripts with any confidence value"
            tone="success"
          />
        </div>
        <ul className="mt-4 space-y-1.5">
          {(performance.data?.notes ?? []).map((note, i) => (
            <li key={i} className="flex items-start gap-2 text-[11px] leading-relaxed text-ink-faint">
              <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-ink-faint" />
              {note}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
