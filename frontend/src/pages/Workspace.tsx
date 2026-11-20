import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  BrainCircuit,
  Clock,
  Cpu,
  Gauge,
  Info,
  Languages as LanguagesIcon,
  Radio,
  Save,
  Sparkles,
  Trash2,
  Volume2,
  Waves,
  Zap,
} from 'lucide-react'
import { MicOrb } from '@/animations/MicOrb'
import { AudioWave } from '@/animations/AudioWave'
import { ProcessingNeural } from '@/animations/ProcessingNeural'
import { useRecorder } from '@/hooks/useRecorder'
import { useApiResource } from '@/hooks/useApiResource'
import { api } from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import { useToast } from '@/components/ui/Toast'
import { Badge, ConfidencePill, EngineBadge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardHeader } from '@/components/ui/Card'
import { Select, Toggle } from '@/components/ui/Field'
import { TranscriptView, SegmentLegend } from '@/components/workspace/TranscriptView'
import { OutputPanel, type OutputTabData } from '@/components/workspace/OutputPanel'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { CONTEXT_LABELS, MODE_LABELS, formatDuration, greeting, languageName, percent } from '@/lib/utils'
import type { OutputMode, SpeechResult } from '@/types'

const MODES: { value: OutputMode; label: string }[] = [
  { value: 'transcribe', label: 'Native script (transcribe)' },
  { value: 'codemix', label: 'Code-mixed (codemix)' },
  { value: 'verbatim', label: 'Verbatim' },
  { value: 'translit', label: 'Romanised (translit)' },
  { value: 'translate', label: 'English (translate)' },
]

export default function Workspace() {
  const { user } = useAuth()
  const { push } = useToast()
  const [mode, setMode] = useState<OutputMode>('transcribe')
  const [context, setContext] = useState('general')
  const [languageCode, setLanguageCode] = useState('auto')
  const [noiseReduction, setNoiseReduction] = useState(false)
  const [retainAudio, setRetainAudio] = useState(false)
  const [result, setResult] = useState<SpeechResult | null>(null)
  const [editedText, setEditedText] = useState('')
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [liveDetect, setLiveDetect] = useState<string | null>(null)

  const engine = useApiResource(() => api.engineStatus(), [])

  const onFinal = useCallback((res: SpeechResult) => {
    setResult(res)
    setEditedText(res.text)
    setDirty(false)
    if (res.demo) push('Demo fixture returned — no speech provider is configured.', 'info')
    else if (res.needs_confirmation) push('Low confidence — please review the transcript.', 'info')
    else push('Transcription saved', 'success')
  }, [push])

  const recorder = useRecorder({
    mode,
    context,
    languageCode: languageCode === 'auto' ? null : languageCode,
    includeOutputs: ['native', 'romanized', 'english'],
    noiseReduction,
    retainAudio,
    onFinal,
    onPartial: (text) => {
      // detect language of the partial text with the real heuristic endpoint
      if (text.length > 12) {
        api
          .detect(text, languageCode === 'auto' ? undefined : languageCode)
          .then((d) => setLiveDetect(d.verdict.code))
          .catch(() => undefined)
      }
    },
    onNotice: (message) => push(message, 'info'),
    onError: (message) => push(message, 'error'),
  })

  useEffect(() => {
    if (recorder.state === 'recording') setLiveDetect(null)
  }, [recorder.state])

  const outputs = result?.outputs ?? {}
  const tabs: OutputTabData[] = useMemo(
    () => [
      { id: 'original', label: 'Original', text: result?.text ?? null, available: Boolean(result?.text), method: result?.mode },
      {
        id: 'native',
        label: 'Native script',
        text: outputs.native?.text ?? (result?.mode === 'transcribe' || result?.mode === 'codemix' ? result?.text ?? null : null),
        available: Boolean(outputs.native?.available || result?.mode === 'transcribe'),
        method: outputs.native?.method,
        reason: outputs.native?.reason,
      },
      {
        id: 'romanized',
        label: 'Romanised',
        text: outputs.romanized?.text ?? (result?.mode === 'translit' ? result?.text ?? null : null),
        available: Boolean(outputs.romanized?.available),
        method: outputs.romanized?.method,
        reason: outputs.romanized?.reason,
      },
      {
        id: 'english',
        label: 'English',
        text: outputs.english?.text ?? (result?.mode === 'translate' ? result?.text ?? null : null),
        available: Boolean(outputs.english?.available),
        method: outputs.english?.method,
        reason: outputs.english?.reason,
      },
      {
        id: 'professional',
        label: 'Professional',
        text: result?.professional_text ?? null,
        available: Boolean(result?.professional_text),
        method: result?.professional_text ? 'rule_based' : undefined,
        reason: 'Use Smart rewrite to produce an email, notes or technical version.',
      },
    ],
    [result, outputs],
  )

  const saveEdit = async () => {
    if (!result) return
    setSaving(true)
    try {
      await api.updateHistory(result.id, { original_text: editedText })
      setResult({ ...result, text: editedText })
      setDirty(false)
      push('Transcript updated', 'success')
    } catch (err) {
      push(err instanceof Error ? err.message : 'Could not save', 'error')
    } finally {
      setSaving(false)
    }
  }

  const rewrite = async (profile: string) => {
    if (!result) return
    try {
      const data = await api.rewrite(result.id, profile)
      setResult({ ...result, professional_text: data.text })
      push(`Rewritten for ${CONTEXT_LABELS[profile] ?? profile} (${data.method})`, 'success')
    } catch (err) {
      push(err instanceof Error ? err.message : 'Rewrite failed', 'error')
    }
  }

  const clearAll = () => {
    recorder.reset()
    setResult(null)
    setEditedText('')
    setDirty(false)
    setLiveDetect(null)
  }

  const recording = recorder.state === 'recording'
  const busy = recorder.state === 'processing' || recorder.state === 'stopping'

  return (
    <div className="space-y-5">
      {/* ---------- header ---------- */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">
            {greeting()}, welcome to BharatVoice
          </h1>
          <p className="mt-1 text-sm text-ink-muted">
            {user?.full_name ? `${user.full_name.split(' ')[0]}, speak` : 'Speak'} naturally in any
            Indian language — language detection is automatic.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={recording ? 'danger' : 'neutral'} icon>
            <Radio className="h-3 w-3" /> {recording ? 'Recording' : recorder.state}
          </Badge>
          <Badge tone="info">{MODE_LABELS[mode] ?? mode}</Badge>
          <Badge tone={engine.data?.primary_available ? 'success' : 'warning'}>
            {engine.data?.primary_engine ?? 'no engine'}
          </Badge>
        </div>
      </div>

      {engine.error && <ErrorState message={engine.error} onRetry={engine.reload} />}

      <div className="grid gap-5 lg:grid-cols-[1.55fr_1fr]">
        {/* ---------- microphone ---------- */}
        <Card className="relative overflow-hidden">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_-10%,rgba(139,92,246,0.18),transparent_60%)]" />
          <div className="relative flex flex-col items-center gap-5 py-4">
            <MicOrb
              state={recorder.state}
              level={recorder.level}
              onStart={() => void recorder.start()}
              onStop={() => void recorder.stop()}
            />

            <div className="text-center">
              <p className="text-lg font-medium text-ink">
                {recorder.state === 'idle' && 'Start speaking'}
                {recorder.state === 'requesting' && 'Requesting microphone…'}
                {recording && 'Listening — speak naturally'}
                {recorder.state === 'stopping' && 'Finishing…'}
                {recorder.state === 'processing' && 'Understanding your speech…'}
                {recorder.state === 'done' && 'Transcription ready'}
                {recorder.state === 'error' && 'Microphone error'}
              </p>
              <p className="mt-1 text-xs text-ink-faint">
                {recording
                  ? `${formatDuration(recorder.elapsed)} · ${recorder.upstream ? 'streaming to Saaras v4' : 'capturing locally'}`
                  : 'Tamil, Hindi, Telugu, Malayalam, Kannada, Bengali, Marathi, Gujarati, Punjabi, Odia, Assamese, Urdu, English'}
              </p>
            </div>

            <div className="w-full">
              <AudioWave values={recorder.waveform} active={recording} height={84} />
            </div>

            <div className="flex w-full flex-wrap items-center justify-center gap-3">
              <span className="flex items-center gap-1.5 text-[11px] text-ink-faint">
                <Volume2 className="h-3.5 w-3.5" /> level
              </span>
              <div className="h-1.5 w-40 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-primary to-accent transition-all duration-100"
                  style={{ width: `${Math.round(recorder.level * 100)}%` }}
                />
              </div>
              <span className="font-mono text-[11px] text-ink-faint">{Math.round(recorder.level * 100)}%</span>
              <Badge tone={recorder.connected ? 'success' : 'neutral'}>
                {recorder.connected ? 'socket open' : 'socket idle'}
              </Badge>
              {recorder.upstream && <Badge tone="info">live partials</Badge>}
            </div>

            {(recording || busy) && (
              <div className="flex items-center gap-2">
                <Badge tone="neutral" icon>
                  <LanguagesIcon className="h-3 w-3" />
                  {liveDetect ? languageName(liveDetect) : 'detecting language…'}
                </Badge>
                <Badge tone="neutral" icon>
                  <Clock className="h-3 w-3" /> max 5 min
                </Badge>
                <Button size="sm" variant="subtle" onClick={recorder.cancel}>
                  Cancel
                </Button>
              </div>
            )}

            {busy && <ProcessingNeural stage={recorder.state === 'processing' ? 3 : 2} />}

            {recorder.partial && recording && (
              <div className="w-full rounded-xl border border-primary/20 bg-primary/[0.06] p-3">
                <p className="mb-1 text-[10px] uppercase tracking-wider text-primary-light">
                  live partial · from streaming model
                </p>
                <p className="indic text-sm text-ink">{recorder.partial}</p>
              </div>
            )}

            {recorder.notice && (
              <p className="flex items-start gap-2 rounded-lg border border-amber-400/25 bg-amber-400/10 px-3 py-2 text-[11px] text-amber-200">
                <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {recorder.notice}
              </p>
            )}

            {recorder.error && (
              <p className="flex items-start gap-2 rounded-lg border border-red-400/25 bg-red-400/10 px-3 py-2 text-[11px] text-red-200">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {recorder.error}
              </p>
            )}
          </div>
        </Card>

        {/* ---------- recognition settings ---------- */}
        <Card>
          <CardHeader
            title="Recognition setup"
            description="Every setting here is sent with the request; nothing is applied silently."
            icon={<Cpu className="h-4 w-4" />}
          />
          <div className="space-y-3">
            <Select
              label="Recognition mode"
              value={mode}
              onChange={(e) => setMode(e.target.value as OutputMode)}
              options={MODES.map((m) => ({ value: m.value, label: m.label }))}
              disabled={recording}
            />
            <Select
              label="Context profile"
              value={context}
              onChange={(e) => setContext(e.target.value)}
              options={Object.entries(CONTEXT_LABELS).map(([value, label]) => ({ value, label }))}
              disabled={recording}
            />
            <Select
              label="Language"
              value={languageCode}
              onChange={(e) => setLanguageCode(e.target.value)}
              options={[
                { value: 'auto', label: 'Auto-detect (recommended)' },
                ...Object.entries({ 'ta-IN': 'Tamil', 'hi-IN': 'Hindi', 'te-IN': 'Telugu', 'ml-IN': 'Malayalam', 'kn-IN': 'Kannada', 'bn-IN': 'Bengali', 'mr-IN': 'Marathi', 'gu-IN': 'Gujarati', 'pa-IN': 'Punjabi', 'or-IN': 'Odia', 'as-IN': 'Assamese', 'ur-IN': 'Urdu', 'en-IN': 'English' }).map(([value, label]) => ({ value, label })),
              ]}
              disabled={recording}
            />
            <div className="divide-y divide-white/[0.06]">
              <Toggle
                label="Noise reduction"
                description="Spectral gate, or DeepFilterNet when installed. Reported as applied only if it really ran."
                checked={noiseReduction}
                onChange={setNoiseReduction}
                disabled={recording}
              />
              <Toggle
                label="Retain this recording's audio"
                description="Off by default. When on, the WAV is stored with the transcript so you can compare."
                checked={retainAudio}
                onChange={setRetainAudio}
                disabled={recording}
              />
            </div>
          </div>
        </Card>
      </div>

      {/* ---------- transcript ---------- */}
      {!result && !busy && (
        <EmptyState
          icon={<Waves className="h-5 w-5" />}
          title="Your transcript will appear here"
          description="Press the microphone and speak. If no speech provider is configured, the backend says so instead of inventing a transcript."
          action={
            <Link to="/app/intelligence">
              <Button size="sm" variant="ghost" icon={<BrainCircuit className="h-3.5 w-3.5" />}>
                Check engine status
              </Button>
            </Link>
          }
        />
      )}

      {result && (
        <div className="grid gap-5 lg:grid-cols-[1.55fr_1fr]">
          <Card>
            <CardHeader
              title="Transcription"
              description={`${result.word_count} words · ${formatDuration(result.duration_seconds)} · ${result.latency_ms ? `${Math.round(result.latency_ms)} ms` : 'streamed'}`}
              icon={<Sparkles className="h-4 w-4" />}
              action={
                <div className="flex flex-wrap items-center justify-end gap-2">
                  <EngineBadge status={result.engine_status} />
                  <ConfidencePill value={result.confidence} source={result.confidence_source} />
                </div>
              }
            />

            {result.demo && (
              <p className="mb-3 flex items-start gap-2 rounded-lg border border-fuchsia-400/30 bg-fuchsia-400/10 px-3 py-2 text-[11px] text-fuchsia-200">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {result.message}
              </p>
            )}

            <div className="rounded-xl border border-white/[0.07] bg-black/25 p-4">
              <TranscriptView segments={result.segments} />
            </div>

            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <SegmentLegend segments={result.segments} />
              <div className="flex flex-wrap items-center gap-2">
                {result.is_code_mixed && (
                  <Badge tone="info">code-mixed · {result.code_switch_count} switch(es)</Badge>
                )}
                <Badge tone="neutral">{result.model_used ?? 'unknown model'}</Badge>
              </div>
            </div>

            <div className="mt-4">
              <label className="label" htmlFor="edit-transcript">
                Edit transcript
              </label>
              <textarea
                id="edit-transcript"
                value={editedText}
                onChange={(e) => {
                  setEditedText(e.target.value)
                  setDirty(e.target.value !== result.text)
                }}
                rows={4}
                className="input prose-indic resize-y"
              />
              <div className="mt-2 flex items-center justify-between gap-2">
                <p className="text-[11px] text-ink-faint">
                  Corrections are stored as edits. Nothing is trained on them unless you approve the
                  word in My Vocabulary.
                </p>
                <Button
                  size="sm"
                  icon={<Save className="h-3.5 w-3.5" />}
                  disabled={!dirty || saving}
                  loading={saving}
                  onClick={saveEdit}
                >
                  Save edit
                </Button>
              </div>
            </div>

            <div className="mt-5">
              <OutputPanel
                tabs={tabs}
                transcriptionId={result.id}
                onGenerated={(id, text) => {
                  setResult({
                    ...result,
                    outputs: {
                      ...result.outputs,
                      [id]: { text, available: true, method: 'generated' },
                    },
                  })
                }}
                onRewrite={rewrite}
              />
            </div>

            <div className="mt-5 flex justify-end">
              <Button variant="ghost" size="sm" icon={<Trash2 className="h-3.5 w-3.5" />} onClick={clearAll}>
                Clear
              </Button>
            </div>
          </Card>

          {/* ---------- routing / engine ---------- */}
          <div className="space-y-5">
            <Card>
              <CardHeader
                title="Routing decision"
                description={result.routing.reason || 'Primary model accepted the transcript.'}
                icon={<Zap className="h-4 w-4" />}
              />
              <div className="space-y-2 text-xs">
                <Row label="Primary model" value={result.routing.primary_model} />
                <Row
                  label="Alternatives used"
                  value={result.routing.alternatives_used.length ? result.routing.alternatives_used.join(', ') : 'none'}
                />
                <Row label="Escalated" value={result.routing.escalated ? 'yes' : 'no'} />
                <Row
                  label="Confidence source"
                  value={
                    result.confidence_source === 'provider'
                      ? 'model-reported'
                      : result.confidence_source === 'proxy'
                        ? 'proxy estimate (uncalibrated)'
                        : 'not available'
                  }
                />
              </div>

              {Object.keys(result.confidence_components).length > 0 && (
                <div className="mt-4 space-y-1.5">
                  <p className="text-[10px] uppercase tracking-wider text-ink-faint">Confidence signals</p>
                  {Object.entries(result.confidence_components).map(([key, value]) => (
                    <div key={key} className="flex items-center gap-2">
                      <span className="w-36 shrink-0 text-[11px] text-ink-muted">{key.replace(/_/g, ' ')}</span>
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                          style={{ width: `${Math.round(Math.min(1, value) * 100)}%` }}
                        />
                      </div>
                      <span className="w-10 text-right font-mono text-[10px] text-ink-faint">{percent(value)}</span>
                    </div>
                  ))}
                </div>
              )}

              {result.routing.trace.length > 0 && (
                <details className="mt-4">
                  <summary className="cursor-pointer text-[11px] text-ink-muted hover:text-ink">
                    Decision trace ({result.routing.trace.length} steps)
                  </summary>
                  <ol className="mt-2 space-y-1.5">
                    {result.routing.trace.map((step, i) => (
                      <li key={i} className="flex items-start gap-2 text-[11px]">
                        <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/70" />
                        <span className="text-ink-faint">
                          <span className="font-mono text-ink-muted">{step.step}</span> · {step.detail}
                        </span>
                      </li>
                    ))}
                  </ol>
                </details>
              )}
            </Card>

            <Card>
              <CardHeader title="Audio report" icon={<Gauge className="h-4 w-4" />} />
              <div className="space-y-2 text-xs">
                <Row label="Duration" value={`${result.audio.duration_seconds.toFixed(2)} s`} />
                <Row label="Peak amplitude" value={String(result.audio.peak)} />
                {result.audio.dbfs !== undefined && <Row label="Level" value={`${result.audio.dbfs} dBFS`} />}
                <Row label="Audio retained" value={result.audio.retained ? 'yes' : 'no (discarded)'} />
                <Row
                  label="Noise reduction"
                  value={
                    (result.audio.noise_reduction as { method?: string } | undefined)?.method ?? 'none'
                  }
                />
                <Row
                  label="Speech detected"
                  value={
                    (result.audio.vad as { speech_seconds?: number } | undefined)?.speech_seconds
                      ? `${(result.audio.vad as { speech_seconds: number }).speech_seconds.toFixed(2)} s`
                      : 'not measured'
                  }
                />
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="text-ink-faint">{label}</span>
      <span className="text-right font-mono text-[11px] text-ink-muted">{value}</span>
    </div>
  )
}
