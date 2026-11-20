import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity,
  BookOpenText,
  BrainCircuit,
  CheckCircle2,
  Gauge,
  Layers,
  LineChart,
  Save,
  Split,
  Target,
  XCircle,
  Zap,
} from 'lucide-react'
import { useApiResource } from '@/hooks/useApiResource'
import { api } from '@/services/api'
import { useToast } from '@/components/ui/Toast'
import { Card, CardHeader, StatCard } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Toggle } from '@/components/ui/Field'
import { ErrorState, LoadingState } from '@/components/ui/States'
import { ModelBarChart } from '@/charts/Charts'
import { CONTEXT_LABELS, percent } from '@/lib/utils'

const CONTEXT_DESCRIPTIONS: Record<string, string> = {
  general: 'Balanced punctuation and casing for everyday dictation.',
  email: 'Removes fillers, expands casual abbreviations, sentence case, full stops.',
  whatsapp: 'Keeps your voice casual; no aggressive normalisation.',
  notes: 'Bullet-friendly, filler-free sentences for lecture notes.',
  academic: 'Formal register, full punctuation, preserves terminology casing.',
  technical: 'Keeps API/CLI terms and identifiers exactly as spoken.',
  code: 'Preserves snake_case, camelCase and symbol names; no casing changes.',
}

export default function AIIntelligence() {
  const engine = useApiResource(() => api.engineStatus(), [])
  const metrics = useApiResource(() => api.routerMetrics(), [])
  const performance = useApiResource(() => api.performance(), [])
  const evaluation = useApiResource(() => api.evaluation(), [])
  const vocabulary = useApiResource(() => api.vocabulary(), [])
  const [policy, setPolicy] = useState({
    enabled: true,
    confidence_threshold: 0.55,
    confirmation_threshold: 0.4,
    max_alternatives: 1,
    latency_budget_ms: 12000,
  })
  const [saving, setSaving] = useState(false)
  const { push } = useToast()

  useEffect(() => {
    if (metrics.data) {
      setPolicy({
        enabled: metrics.data.policy.enabled,
        confidence_threshold: metrics.data.policy.confidence_threshold,
        confirmation_threshold: metrics.data.policy.confirmation_threshold,
        max_alternatives: metrics.data.policy.max_alternatives,
        latency_budget_ms: metrics.data.policy.latency_budget_ms,
      })
    }
  }, [metrics.data])

  const savePolicy = async () => {
    setSaving(true)
    try {
      await api.updatePolicy(policy)
      push('Routing policy updated', 'success')
      metrics.reload()
    } catch (err) {
      push(err instanceof Error ? err.message : 'Could not save policy', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">AI intelligence centre</h1>
          <p className="mt-1 text-sm text-ink-muted">
            The research layer: routing, code-switching, adaptation, context and measured performance.
          </p>
        </div>
        <Badge tone="demo">research modules · shipped code</Badge>
      </div>

      {/* ---------------- Module A ---------------- */}
      <Card>
        <CardHeader
          title="Module A · Adaptive ASR router"
          description="Primary model first. Only uncertain segments are re-run with an alternative, and only within the latency budget."
          icon={<Zap className="h-4 w-4" />}
          action={
            <Badge tone={engine.data?.capabilities?.adaptive_routing ? 'success' : 'neutral'}>
              {engine.data?.capabilities?.adaptive_routing ? 'enabled' : 'disabled'}
            </Badge>
          }
        />

        {engine.loading ? (
          <LoadingState />
        ) : engine.error ? (
          <ErrorState message={engine.error} onRetry={engine.reload} />
        ) : (
          <div className="space-y-4">
            <div className="grid gap-2 sm:grid-cols-2">
              {engine.data?.models.map((model) => (
                <div key={model.model_id} className="rounded-xl border border-white/[0.07] bg-white/[0.02] p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      {model.available ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      ) : (
                        <XCircle className="h-4 w-4 text-ink-faint" />
                      )}
                      <span className="text-sm font-medium text-ink">{model.model_id}</span>
                      {model.is_primary && <Badge tone="info">primary</Badge>}
                    </div>
                    <span className="font-mono text-[10px] text-ink-faint">{model.runtime}</span>
                  </div>
                  <p className="mt-1.5 text-[11px] leading-relaxed text-ink-faint">
                    {model.available ? `modes: ${model.supports_modes.join(', ')}` : model.reason}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {model.supports_streaming && <Badge tone="info">streaming</Badge>}
                    <Badge tone={model.returns_confidence ? 'success' : 'neutral'}>
                      {model.returns_confidence ? 'returns confidence' : 'no confidence'}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>

            <div className="rounded-xl border border-white/[0.07] bg-black/20 p-4">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-ink-faint">Routing policy</h4>
                <span className="text-[10px] text-ink-faint">
                  defaults are engineering starting points, not validated constants
                </span>
              </div>

              <Toggle
                label="Adaptive escalation"
                description="When off, only the primary model runs."
                checked={policy.enabled}
                onChange={(v) => setPolicy({ ...policy, enabled: v })}
              />

              <div className="grid gap-4 pt-3 sm:grid-cols-2">
                <label className="block">
                  <span className="flex items-center justify-between text-[11px] text-ink-muted">
                    Confidence threshold
                    <span className="font-mono text-ink">{policy.confidence_threshold.toFixed(2)}</span>
                  </span>
                  <input
                    type="range"
                    min={0.1}
                    max={0.95}
                    step={0.05}
                    value={policy.confidence_threshold}
                    onChange={(e) => setPolicy({ ...policy, confidence_threshold: Number(e.target.value) })}
                    className="mt-2 w-full accent-primary"
                  />
                </label>
                <label className="block">
                  <span className="flex items-center justify-between text-[11px] text-ink-muted">
                    Confirmation threshold
                    <span className="font-mono text-ink">{policy.confirmation_threshold.toFixed(2)}</span>
                  </span>
                  <input
                    type="range"
                    min={0.05}
                    max={0.9}
                    step={0.05}
                    value={policy.confirmation_threshold}
                    onChange={(e) => setPolicy({ ...policy, confirmation_threshold: Number(e.target.value) })}
                    className="mt-2 w-full accent-primary"
                  />
                </label>
                <label className="block">
                  <span className="flex items-center justify-between text-[11px] text-ink-muted">
                    Max alternative models
                    <span className="font-mono text-ink">{policy.max_alternatives}</span>
                  </span>
                  <input
                    type="range"
                    min={0}
                    max={3}
                    step={1}
                    value={policy.max_alternatives}
                    onChange={(e) => setPolicy({ ...policy, max_alternatives: Number(e.target.value) })}
                    className="mt-2 w-full accent-primary"
                  />
                </label>
                <label className="block">
                  <span className="flex items-center justify-between text-[11px] text-ink-muted">
                    Latency budget
                    <span className="font-mono text-ink">{policy.latency_budget_ms} ms</span>
                  </span>
                  <input
                    type="range"
                    min={1000}
                    max={30000}
                    step={500}
                    value={policy.latency_budget_ms}
                    onChange={(e) => setPolicy({ ...policy, latency_budget_ms: Number(e.target.value) })}
                    className="mt-2 w-full accent-primary"
                  />
                </label>
              </div>

              <div className="mt-4 flex justify-end">
                <Button size="sm" icon={<Save className="h-3.5 w-3.5" />} loading={saving} onClick={savePolicy}>
                  Save policy
                </Button>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-4">
              <StatCard label="Decisions" value={metrics.data?.decisions ?? 0} icon={<Activity className="h-4 w-4" />} />
              <StatCard
                label="Escalations"
                value={metrics.data?.escalations ?? 0}
                hint={metrics.data?.escalation_rate !== null ? `${percent(metrics.data?.escalation_rate ?? 0)} of requests` : 'no data'}
                tone="accent"
                icon={<Layers className="h-4 w-4" />}
              />
              <StatCard
                label="Avg latency"
                value={metrics.data?.average_latency_ms ? `${Math.round(metrics.data.average_latency_ms)} ms` : '—'}
                tone="success"
                icon={<Gauge className="h-4 w-4" />}
              />
              <StatCard
                label="Calibration"
                value={metrics.data?.calibration.fitted ? 'fitted' : 'unfitted'}
                hint={`${metrics.data?.calibration.samples ?? 0} samples`}
                tone="muted"
                icon={<Target className="h-4 w-4" />}
              />
            </div>

            <p className="rounded-lg border border-amber-400/20 bg-amber-400/[0.06] px-3 py-2 text-[11px] leading-relaxed text-amber-100/90">
              {metrics.data?.calibration.note ??
                'Proxy scores are uncalibrated until a calibrator is fitted on labelled evaluation data.'}
            </p>
          </div>
        )}
      </Card>

      {/* ---------------- Module B ---------------- */}
      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Module B · Code-switch detection"
            description="Per-token attribution with a visual timeline. Ambiguity is surfaced, not hidden."
            icon={<Split className="h-4 w-4" />}
            action={
              <Link to="/app/languages" className="text-xs text-ink-muted hover:text-ink">
                Open analyser
              </Link>
            }
          />
          <div className="space-y-2">
            {[
              ['Tamil + English', 'Bro inniku college ku late ah varuven because traffic romba jasthi', 'ta-IN'],
              ['Hindi + English', 'Kal meeting hai presentation ready karna hai deadline Friday tak', 'hi-IN'],
              ['Telugu + English', 'Repo ki pull request pampinchu, tests pass ayyayi', 'te-IN'],
            ].map(([label, text, code]) => (
              <button
                key={label}
                onClick={() => {
                  navigator.clipboard?.writeText(text).catch(() => undefined)
                  push('Sample copied — paste it in the analyser', 'info')
                }}
                className="w-full rounded-xl border border-white/[0.07] bg-white/[0.02] p-3 text-left transition-colors hover:border-primary/25"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium uppercase tracking-wider text-ink-faint">{label}</span>
                  <span className="font-mono text-[10px] text-ink-faint">{code}</span>
                </div>
                <p className="indic mt-1.5 text-sm text-ink">{text}</p>
              </button>
            ))}
          </div>
          <p className="mt-3 text-[11px] leading-relaxed text-ink-faint">
            Supported pairs in code: Tamil–English, Hindi–English, Telugu–English, Malayalam–English,
            Kannada–English. Other pairs work to the extent their scripts and lexicons are covered.
          </p>
        </Card>

        {/* ---------------- Module C ---------------- */}
        <Card>
          <CardHeader
            title="Module C · Personal dialect intelligence"
            description="A dictionary and a decoder hint. Not acoustic fine-tuning — we do not claim otherwise."
            icon={<BookOpenText className="h-4 w-4" />}
            action={
              <Link to="/app/vocabulary" className="text-xs text-ink-muted hover:text-ink">
                Manage
              </Link>
            }
          />
          <div className="grid gap-3 sm:grid-cols-3">
            <StatCard label="Approved words" value={vocabulary.data?.length ?? 0} tone="primary" />
            <StatCard
              label="Used in transcripts"
              value={vocabulary.data?.filter((v) => v.usage_count > 0).length ?? 0}
              tone="accent"
            />
            <StatCard
              label="From corrections"
              value={vocabulary.data?.filter((v) => v.source === 'correction').length ?? 0}
              tone="success"
            />
          </div>
          <ul className="mt-4 space-y-1.5">
            {(vocabulary.data ?? []).slice(0, 5).map((entry) => (
              <li key={entry.id} className="flex items-center justify-between gap-2 rounded-lg border border-white/[0.06] px-3 py-2 text-xs">
                <span className="min-w-0">
                  <span className="text-ink">{entry.preferred_spelling}</span>
                  <span className="ml-2 text-ink-faint">{entry.category.replace('_', ' ')}</span>
                </span>
                <Badge tone={entry.is_active ? 'success' : 'neutral'}>{entry.is_active ? 'active' : 'paused'}</Badge>
              </li>
            ))}
            {(vocabulary.data?.length ?? 0) === 0 && (
              <li className="rounded-lg border border-dashed border-white/10 px-3 py-4 text-center text-xs text-ink-faint">
                No vocabulary yet. Add names and technical terms to bias recognition.
              </li>
            )}
          </ul>
          <p className="mt-3 text-[11px] leading-relaxed text-ink-faint">
            Acoustic speaker adaptation is a documented future extension, not a shipped feature.
          </p>
        </Card>
      </div>

      {/* ---------------- Module D ---------------- */}
      <Card>
        <CardHeader
          title="Module D · Contextual intelligence"
          description="The context profile is applied after recognition. It fixes form, never meaning."
          icon={<BrainCircuit className="h-4 w-4" />}
        />
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {Object.entries(CONTEXT_LABELS).map(([key, label]) => (
            <div key={key} className="rounded-xl border border-white/[0.07] bg-white/[0.02] p-3">
              <p className="text-xs font-medium text-ink">{label}</p>
              <p className="mt-1 text-[11px] leading-relaxed text-ink-faint">{CONTEXT_DESCRIPTIONS[key]}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* ---------------- Module E ---------------- */}
      <Card>
        <CardHeader
          title="Module E · Model performance"
          description="Only measured numbers. Unmeasured metrics are labelled, not estimated."
          icon={<LineChart className="h-4 w-4" />}
        />
        {performance.loading ? (
          <LoadingState />
        ) : (
          <div className="grid gap-5 lg:grid-cols-2">
            <div>
              <div className="grid gap-3 sm:grid-cols-2">
                <StatCard
                  label="Word error rate"
                  value={evaluation.data?.wer !== null && evaluation.data?.wer !== undefined ? percent(evaluation.data.wer, 1) : 'not measured'}
                  hint="requires reference transcripts"
                  tone="muted"
                  icon={<Target className="h-4 w-4" />}
                />
                <StatCard
                  label="Character error rate"
                  value={evaluation.data?.cer !== null && evaluation.data?.cer !== undefined ? percent(evaluation.data.cer, 1) : 'not measured'}
                  hint="requires reference transcripts"
                  tone="muted"
                  icon={<Target className="h-4 w-4" />}
                />
                <StatCard
                  label="Avg latency"
                  value={performance.data?.average_latency_ms ? `${Math.round(performance.data.average_latency_ms)} ms` : '—'}
                  hint={`p95 ${performance.data?.p95_latency_ms ? Math.round(performance.data.p95_latency_ms) + ' ms' : '—'}`}
                  tone="accent"
                />
                <StatCard
                  label="Confidence coverage"
                  value={percent(performance.data?.confidence_coverage ?? 0)}
                  hint="share of transcripts with any confidence"
                  tone="primary"
                />
              </div>
              <ul className="mt-3 space-y-1.5">
                {(performance.data?.notes ?? []).concat(evaluation.data?.notes ?? []).map((note, i) => (
                  <li key={i} className="flex items-start gap-2 text-[11px] leading-relaxed text-ink-faint">
                    <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-ink-faint" />
                    {note}
                  </li>
                ))}
              </ul>
              <p className="mt-3 rounded-lg border border-white/[0.08] bg-white/[0.02] px-3 py-2 text-[11px] leading-relaxed text-ink-muted">
                {evaluation.data?.reason ?? 'Run the evaluation harness to produce a real report.'}
              </p>
            </div>
            <div>
              <h4 className="mb-2 text-[11px] uppercase tracking-wider text-ink-faint">Model usage</h4>
              <ModelBarChart
                data={Object.entries(performance.data?.model_usage ?? {}).map(([name, count]) => ({ name, count }))}
              />
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
