import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Copy, Download, Filter, Mic, Search, Trash2 } from 'lucide-react'
import { useApiResource } from '@/hooks/useApiResource'
import { api } from '@/services/api'
import { useToast } from '@/components/ui/Toast'
import { Card } from '@/components/ui/Card'
import { Badge, ConfidencePill, EngineBadge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input, Select } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { EmptyState, ErrorState, SkeletonRows } from '@/components/ui/States'
import { TranscriptView } from '@/components/workspace/TranscriptView'
import { LANGUAGE_META, copyText, downloadText, formatDate, formatDuration, languageName } from '@/lib/utils'
import type { Transcription } from '@/types'

export default function History() {
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [language, setLanguage] = useState('')
  const [sort, setSort] = useState<'desc' | 'asc'>('desc')
  const [page, setPage] = useState(1)
  const [openId, setOpenId] = useState<string | null>(params.get('open'))
  const [detail, setDetail] = useState<Transcription | null>(null)
  const { push } = useToast()

  const list = useApiResource(
    () => api.history({ page, page_size: 8, search: search || undefined, language: language || undefined, sort }),
    [page, search, language, sort],
  )

  useEffect(() => {
    if (!openId) {
      setDetail(null)
      return
    }
    api
      .historyItem(openId)
      .then(setDetail)
      .catch(() => push('Could not open that transcription', 'error'))
  }, [openId, push])

  const remove = async (item: Transcription) => {
    try {
      await api.deleteHistory(item.id)
      push('Transcription deleted', 'success')
      if (openId === item.id) {
        setOpenId(null)
        params.delete('open')
        setParams(params)
      }
      list.reload()
    } catch (err) {
      push(err instanceof Error ? err.message : 'Delete failed', 'error')
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">History</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Every stored transcription with the engine that produced it. Deleting removes it from your
          account.
        </p>
      </div>

      <Card>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Input
            placeholder="Search transcripts…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            icon={<Search className="h-4 w-4" />}
            className="flex-1"
          />
          <Select
            value={language}
            onChange={(e) => {
              setLanguage(e.target.value)
              setPage(1)
            }}
            options={[
              { value: '', label: 'All languages' },
              ...Object.entries(LANGUAGE_META).map(([code, meta]) => ({ value: code, label: meta.name })),
            ]}
            className="sm:w-44"
          />
          <Select
            value={sort}
            onChange={(e) => setSort(e.target.value as 'asc' | 'desc')}
            options={[
              { value: 'desc', label: 'Newest first' },
              { value: 'asc', label: 'Oldest first' },
            ]}
            className="sm:w-40"
          />
        </div>

        <div className="mt-4">
          {list.loading ? (
            <SkeletonRows rows={4} />
          ) : list.error ? (
            <ErrorState message={list.error} onRetry={list.reload} />
          ) : (list.data?.items.length ?? 0) === 0 ? (
            <EmptyState
              icon={<Mic className="h-5 w-5" />}
              title={search || language ? 'No transcripts match those filters' : 'Nothing recorded yet'}
              description="Record something in the workspace and it will appear here with its language mix, model and engine status."
            />
          ) : (
            <ul className="space-y-2">
              {list.data?.items.map((item) => (
                <li
                  key={item.id}
                  className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 transition-colors hover:border-primary/25"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <button className="min-w-0 flex-1 text-left" onClick={() => setOpenId(item.id)}>
                      <p className="truncate text-sm font-medium text-ink">{item.title}</p>
                      <p className="mt-0.5 line-clamp-2 text-xs text-ink-muted">{item.original_text}</p>
                      <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        <EngineBadge status={item.engine_status} />
                        <ConfidencePill value={item.confidence} source={item.confidence_source} />
                        {item.detected_languages.map((code) => (
                          <Badge key={code} tone="neutral">
                            {languageName(code)}
                          </Badge>
                        ))}
                        {item.is_code_mixed && <Badge tone="info">{item.code_switch_count} switches</Badge>}
                      </div>
                    </button>
                    <div className="flex flex-col items-end gap-2">
                      <p className="text-[11px] text-ink-faint">{formatDate(item.created_at)}</p>
                      <div className="flex items-center gap-1">
                        <span className="mr-1 font-mono text-[10px] text-ink-faint">
                          {formatDuration(item.duration_seconds)} · {item.word_count}w
                        </span>
                        <Button
                          size="sm"
                          variant="subtle"
                          aria-label="Copy transcript"
                          onClick={async () => {
                            const ok = await copyText(item.original_text)
                            push(ok ? 'Copied' : 'Clipboard blocked', ok ? 'success' : 'error')
                          }}
                        >
                          <Copy className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          size="sm"
                          variant="subtle"
                          aria-label="Download transcript"
                          onClick={() => downloadText(`bharatvoice-${item.id}.txt`, item.original_text)}
                        >
                          <Download className="h-3.5 w-3.5" />
                        </Button>
                        <Button size="sm" variant="subtle" aria-label="Delete transcript" onClick={() => remove(item)}>
                          <Trash2 className="h-3.5 w-3.5 text-red-300" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {list.data && list.data.pages > 1 && (
          <div className="mt-4 flex items-center justify-between">
            <p className="text-[11px] text-ink-faint">
              Page {list.data.page} of {list.data.pages} · {list.data.total} transcriptions
            </p>
            <div className="flex gap-1">
              <Button
                size="sm"
                variant="ghost"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                icon={<ChevronLeft className="h-3.5 w-3.5" />}
              >
                Prev
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={page >= list.data.pages}
                onClick={() => setPage((p) => p + 1)}
                iconRight={<ChevronRight className="h-3.5 w-3.5" />}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>

      <Modal
        open={Boolean(openId)}
        onClose={() => {
          setOpenId(null)
          params.delete('open')
          setParams(params)
        }}
        title={detail?.title ?? 'Transcription'}
        width="max-w-2xl"
        footer={
          <>
            {detail && (
              <Button
                variant="ghost"
                icon={<Download className="h-3.5 w-3.5" />}
                onClick={() => downloadText(`bharatvoice-${detail.id}.txt`, detail.original_text)}
              >
                Download
              </Button>
            )}
            <Button
              variant="ghost"
              onClick={() => {
                setOpenId(null)
                params.delete('open')
                setParams(params)
              }}
            >
              Close
            </Button>
          </>
        }
      >
        {detail ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-1.5">
              <EngineBadge status={detail.engine_status} />
              <ConfidencePill value={detail.confidence} source={detail.confidence_source} />
              <Badge tone="neutral">{detail.model_used ?? 'unknown model'}</Badge>
              <Badge tone="neutral">{detail.output_mode}</Badge>
              {detail.audio_retained && <Badge tone="warning">audio retained</Badge>}
            </div>

            <div className="rounded-xl border border-white/[0.07] bg-black/25 p-3">
              <TranscriptView segments={detail.segments.length ? detail.segments : [{ text: detail.original_text }]} />
            </div>

            <div className="grid gap-2 text-xs sm:grid-cols-2">
              <Field label="Created" value={formatDate(detail.created_at)} />
              <Field label="Duration" value={formatDuration(detail.duration_seconds)} />
              <Field label="Words" value={String(detail.word_count)} />
              <Field label="Edits" value={String(detail.edit_count)} />
              <Field label="Context" value={detail.context_profile} />
              <Field label="Latency" value={detail.latency_ms ? `${Math.round(detail.latency_ms)} ms` : '—'} />
            </div>

            {detail.english_text && (
              <div>
                <p className="label">English</p>
                <p className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3 text-sm text-ink">
                  {detail.english_text}
                </p>
              </div>
            )}
            {detail.romanized_text && (
              <div>
                <p className="label">Romanised</p>
                <p className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3 text-sm text-ink">
                  {detail.romanized_text}
                </p>
              </div>
            )}
            {detail.professional_text && (
              <div>
                <p className="label">Professional</p>
                <p className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3 text-sm text-ink">
                  {detail.professional_text}
                </p>
              </div>
            )}
          </div>
        ) : (
          <SkeletonRows rows={3} />
        )}
      </Modal>
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-white/[0.06] px-3 py-2">
      <span className="text-ink-faint">{label}</span>
      <span className="font-mono text-[11px] text-ink-muted">{value}</span>
    </div>
  )
}
