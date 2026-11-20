import { useEffect, useState } from 'react'
import { ArrowRight, Check, Languages as LanguagesIcon, Plus, Search, Split, Star } from 'lucide-react'
import { useApiResource } from '@/hooks/useApiResource'
import { api } from '@/services/api'
import { useToast } from '@/components/ui/Toast'
import { Card, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Field'
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States'
import type { DetectResponse } from '@/types'
import { cn, languageName, percent } from '@/lib/utils'

const EXAMPLE = 'Tomorrow meeting ku presentation ready pannidu'

export default function LanguageIntelligence() {
  const languages = useApiResource(() => api.languages(), [])
  const usage = useApiResource(() => api.languageUsage(), [])
  const settings = useApiResource(() => api.settings(), [])
  const [preferred, setPreferred] = useState<string[]>([])
  const [sample, setSample] = useState(EXAMPLE)
  const [analysis, setAnalysis] = useState<DetectResponse | null>(null)
  const [analysing, setAnalysing] = useState(false)
  const { push } = useToast()

  useEffect(() => {
    if (settings.data) setPreferred(settings.data.preferred_languages)
  }, [settings.data])

  const runAnalysis = async (text: string) => {
    if (!text.trim()) return
    setAnalysing(true)
    try {
      setAnalysis(await api.detect(text))
    } catch (err) {
      push(err instanceof Error ? err.message : 'Language analysis failed', 'error')
    } finally {
      setAnalysing(false)
    }
  }

  useEffect(() => {
    void runAnalysis(EXAMPLE)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const togglePreferred = async (code: string) => {
    const next = preferred.includes(code) ? preferred.filter((c) => c !== code) : [...preferred, code]
    setPreferred(next)
    try {
      await api.updateSettings({ preferred_languages: next })
      push(next.includes(code) ? `${languageName(code)} added to preferred languages` : `${languageName(code)} removed`, 'success')
    } catch {
      push('Could not update preferences', 'error')
    }
  }

  const usageByCode = new Map((usage.data ?? []).map((u) => [u.code, u]))

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Language intelligence</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Which languages are configured, which ones your voice actually uses, and where a sentence
          switches between them.
        </p>
      </div>

      {/* ---------- mixing visualiser ---------- */}
      <Card>
        <CardHeader
          title="Language-mixing analyser"
          description="Token-level attribution with explicit uncertainty. Script + lexicon heuristic over text — not an acoustic LID score."
          icon={<Split className="h-4 w-4" />}
          action={<Badge tone="info">live analysis</Badge>}
        />
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            value={sample}
            onChange={(e) => setSample(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && runAnalysis(sample)}
            placeholder="Type a code-mixed sentence…"
            icon={<Search className="h-4 w-4" />}
            className="flex-1"
          />
          <Button onClick={() => runAnalysis(sample)} loading={analysing} iconRight={<ArrowRight className="h-4 w-4" />}>
            Analyse
          </Button>
        </div>

        {analysis && (
          <div className="mt-4 space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="neutral">
                primary: {languageName(analysis.verdict.code)} · {percent(analysis.verdict.confidence)} heuristic
              </Badge>
              <Badge tone={analysis.code_switching.is_code_mixed ? 'info' : 'neutral'}>
                {analysis.code_switching.switch_count} switch(es) · ratio {percent(analysis.code_switching.code_mixed_ratio)}
              </Badge>
              {analysis.code_switching.uncertain_tokens > 0 && (
                <Badge tone="warning">{analysis.code_switching.uncertain_tokens} uncertain token(s)</Badge>
              )}
              {analysis.verdict.ambiguous_with.length > 0 && (
                <Badge tone="warning">
                  shared script with {analysis.verdict.ambiguous_with.map(languageName).join(', ')}
                </Badge>
              )}
            </div>

            <div className="flex flex-wrap gap-1.5">
              {analysis.code_switching.spans.map((span, i) => (
                <span
                  key={`${span.text}-${i}`}
                  className={cn(
                    'inline-flex flex-col rounded-lg border px-2.5 py-1.5 text-sm',
                    span.kind === 'matrix'
                      ? 'border-primary/40 bg-primary/10 text-primary-light'
                      : span.kind === 'embedded'
                        ? 'border-accent/40 bg-accent/10 text-accent-light'
                        : 'border-dashed border-white/25 bg-white/[0.04] text-ink-faint',
                  )}
                >
                  <span>{span.text}</span>
                  <span className="text-[9px] uppercase tracking-wider opacity-80">
                    {span.kind === 'uncertain' ? 'uncertain' : span.language_name} · {span.kind}
                  </span>
                </span>
              ))}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="text-[10px] uppercase tracking-wider text-ink-faint">
                  <tr>
                    <th className="py-1.5 pr-3">Token</th>
                    <th className="py-1.5 pr-3">Language</th>
                    <th className="py-1.5 pr-3">Evidence</th>
                    <th className="py-1.5">Confidence</th>
                  </tr>
                </thead>
                <tbody className="text-ink-muted">
                  {analysis.code_switching.tokens.map((t, i) => (
                    <tr key={`${t.token}-${i}`} className="border-t border-white/[0.05]">
                      <td className="py-1.5 pr-3 font-mono text-ink">{t.token}</td>
                      <td className="py-1.5 pr-3">{languageName(t.language)}</td>
                      <td className="py-1.5 pr-3 text-ink-faint">
                        {t.evidence}
                        {t.uncertain && <span className="ml-1 text-amber-300">(uncertain)</span>}
                      </td>
                      <td className="py-1.5 font-mono">{percent(t.confidence)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Card>

      {/* ---------- language cards ---------- */}
      <div>
        <div className="mb-3 flex items-end justify-between">
          <div>
            <h2 className="text-sm font-semibold text-ink">Configured languages</h2>
            <p className="text-xs text-ink-faint">Recognition support reflects the configured model, not aspiration.</p>
          </div>
          <Badge tone="neutral">{languages.data?.length ?? 0} languages</Badge>
        </div>

        {languages.loading ? (
          <LoadingState />
        ) : languages.error ? (
          <ErrorState message={languages.error} onRetry={languages.reload} />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {languages.data?.map((language) => {
              const stat = usageByCode.get(language.code)
              const isPreferred = preferred.includes(language.code)
              return (
                <Card key={language.code} className="card-hover">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="indic truncate text-lg font-semibold text-ink">{language.native_name}</p>
                      <p className="mt-0.5 text-[11px] text-ink-faint">
                        {language.name} · {language.script} ·{' '}
                        <span className="font-mono">{language.code}</span>
                      </p>
                    </div>
                    <button
                      onClick={() => togglePreferred(language.code)}
                      className={cn(
                        'rounded-lg border p-1.5 transition-colors',
                        isPreferred
                          ? 'border-amber-400/40 bg-amber-400/10 text-amber-300'
                          : 'border-white/10 text-ink-faint hover:text-ink',
                      )}
                      aria-label={isPreferred ? 'Remove from preferred' : 'Add to preferred'}
                      title={isPreferred ? 'Preferred language' : 'Add to preferred languages'}
                    >
                      {isPreferred ? <Star className="h-3.5 w-3.5 fill-current" /> : <Plus className="h-3.5 w-3.5" />}
                    </button>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    {language.recognition_supported ? (
                      <Badge tone="success" icon>
                        recognition supported
                      </Badge>
                    ) : (
                      <Badge tone="neutral">not configured</Badge>
                    )}
                  </div>

                  <div className="mt-3 grid grid-cols-2 gap-2 text-[11px]">
                    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-2">
                      <p className="text-ink-faint">Your usage</p>
                      <p className="mt-0.5 font-mono text-ink">{stat?.count ?? 0} sessions</p>
                    </div>
                    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-2">
                      <p className="text-ink-faint">Words</p>
                      <p className="mt-0.5 font-mono text-ink">{stat?.words ?? 0}</p>
                    </div>
                  </div>

                  <p className="mt-2 text-[10px] leading-relaxed text-ink-faint">
                    Per-language recognition confidence is not shown: the primary model does not
                    return one, and we will not invent it.
                  </p>
                </Card>
              )
            })}
          </div>
        )}
      </div>

      {!languages.loading && languages.data?.length === 0 && (
        <EmptyState
          icon={<LanguagesIcon className="h-5 w-5" />}
          title="No languages configured"
          description="Run the backend seed (`python -m app.database.init_db`) to load the reference language list."
        />
      )}

      <Card>
        <CardHeader title="How language detection actually works here" icon={<Check className="h-4 w-4" />} />
        <ul className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <li>
            <span className="text-ink">Acoustic language ID</span> comes from the ASR provider
            (Saaras reports a language code, and a probability when it has one).
          </li>
          <li>
            <span className="text-ink">Token attribution</span> is ours: Unicode script ranges plus a
            romanised-lexicon for Latin-script Indic words. Confidence values from this path are
            labelled <span className="font-mono text-[11px] text-ink">heuristic</span>.
          </li>
          <li>
            <span className="text-ink">Shared scripts</span> (Devanagari for Hindi/Marathi, Bengali for
            Bengali/Assamese) are reported as ambiguous instead of silently guessed.
          </li>
        </ul>
      </Card>
    </div>
  )
}
