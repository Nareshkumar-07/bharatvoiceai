import { useState } from 'react'
import { Copy, Download, Languages, Loader2, Sparkles, Type } from 'lucide-react'
import { Tabs } from '@/components/ui/Tabs'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { copyText, downloadText, CONTEXT_LABELS } from '@/lib/utils'
import { useToast } from '@/components/ui/Toast'
import { api } from '@/services/api'
import type { OutputVariant } from '@/types'

export interface OutputTabData {
  id: string
  label: string
  text: string | null
  available: boolean
  method?: string
  reason?: string | null
}

interface Props {
  tabs: OutputTabData[]
  transcriptionId?: string
  onGenerated?: (id: string, text: string) => void
  onRewrite?: (profile: string) => Promise<void>
}

export function OutputPanel({ tabs, transcriptionId, onGenerated, onRewrite }: Props) {
  const [active, setActive] = useState(tabs[0]?.id ?? 'original')
  const [busy, setBusy] = useState<string | null>(null)
  const [rewriteProfile, setRewriteProfile] = useState('email')
  const { push } = useToast()

  const current = tabs.find((t) => t.id === active) ?? tabs[0]

  const generate = async (kind: 'native' | 'romanized' | 'english') => {
    if (!transcriptionId) return
    setBusy(kind)
    try {
      const res = await api.generateOutput(transcriptionId, kind)
      if (res.available && res.text) {
        onGenerated?.(kind, res.text)
        push(`${kind} output generated (${res.method ?? 'model'})`, 'success')
      } else {
        push(res.reason ?? `${kind} is unavailable: no backend is configured`, 'error')
      }
    } catch (err) {
      push(err instanceof Error ? err.message : 'Could not generate output', 'error')
    } finally {
      setBusy(null)
    }
  }

  const copy = async () => {
    if (!current?.text) return
    const ok = await copyText(current.text)
    push(ok ? 'Copied to clipboard' : 'Clipboard is blocked in this context', ok ? 'success' : 'error')
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs
          items={tabs.map((t) => ({
            id: t.id,
            label: t.label,
            badge: !t.available ? (
              <span className="ml-1 rounded bg-white/10 px-1 text-[9px] uppercase text-ink-faint">n/a</span>
            ) : undefined,
          }))}
          value={active}
          onChange={setActive}
        />
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" icon={<Copy className="h-3.5 w-3.5" />} onClick={copy} disabled={!current?.text}>
            Copy
          </Button>
          <Button
            variant="ghost"
            size="sm"
            icon={<Download className="h-3.5 w-3.5" />}
            onClick={() =>
              downloadText(`bharatvoice-${current?.id ?? 'output'}.txt`, current?.text ?? '')
            }
            disabled={!current?.text}
          >
            Download
          </Button>
        </div>
      </div>

      <div className="min-h-[7rem] rounded-xl border border-white/[0.07] bg-black/25 p-4">
        {current?.text ? (
          <p className="prose-indic whitespace-pre-wrap text-sm leading-relaxed text-ink">{current.text}</p>
        ) : (
          <div className="flex flex-col items-start gap-3">
            <p className="text-xs text-ink-faint">
              {current?.reason ??
                'This output has not been generated yet. Generating it calls a real model — nothing is invented locally.'}
            </p>
            {current && ['native', 'romanized', 'english'].includes(current.id) && transcriptionId && (
              <Button
                size="sm"
                variant="ghost"
                loading={busy === current.id}
                icon={<Languages className="h-3.5 w-3.5" />}
                onClick={() => generate(current.id as 'native' | 'romanized' | 'english')}
              >
                Generate {current.label.toLowerCase()}
              </Button>
            )}
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {current?.method && <Badge tone="neutral">{current.method}</Badge>}
        {current?.available && current.text && <Badge tone="success">generated</Badge>}
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <span className="text-[11px] text-ink-faint">Smart rewrite</span>
          <select
            className="input w-auto px-2 py-1 text-[11px]"
            value={rewriteProfile}
            onChange={(e) => setRewriteProfile(e.target.value)}
            aria-label="Rewrite profile"
          >
            {Object.entries(CONTEXT_LABELS).map(([value, label]) => (
              <option key={value} value={value} className="bg-canvas-700">
                {label}
              </option>
            ))}
          </select>
          <Button
            size="sm"
            variant="ghost"
            icon={busy === 'rewrite' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
            disabled={!transcriptionId || busy === 'rewrite'}
            onClick={async () => {
              if (!onRewrite) return
              setBusy('rewrite')
              try {
                await onRewrite(rewriteProfile)
                setActive('professional')
              } finally {
                setBusy(null)
              }
            }}
          >
            Rewrite
          </Button>
        </div>
      </div>
    </div>
  )
}
