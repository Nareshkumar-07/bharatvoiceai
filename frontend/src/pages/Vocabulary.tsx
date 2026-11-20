import { useMemo, useState } from 'react'
import { Download, Pencil, Plus, Search, Trash2, Upload } from 'lucide-react'
import { useApiResource } from '@/hooks/useApiResource'
import { api } from '@/services/api'
import { useToast } from '@/components/ui/Toast'
import { Card, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input, Select } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { EmptyState, ErrorState, SkeletonRows } from '@/components/ui/States'
import { LANGUAGE_META, formatRelative } from '@/lib/utils'
import type { VocabularyEntry } from '@/types'

const CATEGORIES = [
  { value: 'general', label: 'General word' },
  { value: 'personal_name', label: 'Personal name' },
  { value: 'place', label: 'Place' },
  { value: 'technical', label: 'Technical term' },
  { value: 'brand', label: 'Brand' },
  { value: 'acronym', label: 'Acronym' },
]

const EMPTY_FORM = {
  word: '',
  preferred_spelling: '',
  category: 'general',
  language_code: 'en-IN',
  pronunciation_hint: '',
  weight: 1,
}

export default function Vocabulary() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const vocabulary = useApiResource(() => api.vocabulary({ search: search || undefined, category: category || undefined }), [search, category])
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<VocabularyEntry | null>(null)
  const [form, setForm] = useState({ ...EMPTY_FORM })
  const [saving, setSaving] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [importText, setImportText] = useState('')
  const { push } = useToast()

  const openCreate = () => {
    setEditing(null)
    setForm({ ...EMPTY_FORM })
    setModalOpen(true)
  }

  const openEdit = (entry: VocabularyEntry) => {
    setEditing(entry)
    setForm({
      word: entry.word,
      preferred_spelling: entry.preferred_spelling,
      category: entry.category,
      language_code: entry.language_code,
      pronunciation_hint: entry.pronunciation_hint ?? '',
      weight: entry.weight,
    })
    setModalOpen(true)
  }

  const submit = async () => {
    if (!form.word.trim() || !form.preferred_spelling.trim()) {
      push('Word and preferred spelling are required', 'error')
      return
    }
    setSaving(true)
    try {
      if (editing) {
        await api.updateVocabulary(editing.id, form)
        push('Entry updated', 'success')
      } else {
        await api.createVocabulary(form)
        push('Entry added', 'success')
      }
      setModalOpen(false)
      vocabulary.reload()
    } catch (err) {
      push(err instanceof Error ? err.message : 'Could not save entry', 'error')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (entry: VocabularyEntry) => {
    try {
      await api.deleteVocabulary(entry.id)
      push('Entry deleted', 'success')
      vocabulary.reload()
    } catch (err) {
      push(err instanceof Error ? err.message : 'Could not delete entry', 'error')
    }
  }

  const toggleActive = async (entry: VocabularyEntry) => {
    try {
      await api.updateVocabulary(entry.id, { is_active: !entry.is_active })
      vocabulary.reload()
    } catch {
      push('Could not update entry', 'error')
    }
  }

  const runImport = async () => {
    try {
      const parsed = JSON.parse(importText) as Partial<VocabularyEntry>[]
      if (!Array.isArray(parsed)) throw new Error('Expected a JSON array of entries')
      const res = await api.importVocabulary(parsed)
      push(`Imported ${res.created}, skipped ${res.skipped}`, 'success')
      setImportOpen(false)
      setImportText('')
      vocabulary.reload()
    } catch (err) {
      push(err instanceof Error ? err.message : 'Import failed', 'error')
    }
  }

  const grouped = useMemo(() => {
    const map = new Map<string, VocabularyEntry[]>()
    for (const entry of vocabulary.data ?? []) {
      const key = entry.category
      map.set(key, [...(map.get(key) ?? []), entry])
    }
    return Array.from(map.entries())
  }, [vocabulary.data])

  const downloadExport = async (fmt: 'json' | 'csv') => {
    try {
      const res = await fetch(api.exportVocabularyUrl(fmt), {
        headers: { Authorization: `Bearer ${localStorage.getItem('bharatvoice.access') ?? ''}` },
      })
      if (!res.ok) throw new Error(`Export failed (${res.status})`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `bharatvoice-vocabulary.${fmt}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      push(err instanceof Error ? err.message : 'Export failed', 'error')
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">My vocabulary</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Names, places and terms you want recognised. Sent to the model as keyterms and applied as
            guarded spelling rules.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" size="sm" icon={<Upload className="h-3.5 w-3.5" />} onClick={() => setImportOpen(true)}>
            Import
          </Button>
          <Button variant="ghost" size="sm" icon={<Download className="h-3.5 w-3.5" />} onClick={() => downloadExport('json')}>
            Export JSON
          </Button>
          <Button size="sm" icon={<Plus className="h-3.5 w-3.5" />} onClick={openCreate}>
            Add word
          </Button>
        </div>
      </div>

      <Card>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Input
            placeholder="Search words…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            icon={<Search className="h-4 w-4" />}
            className="flex-1"
          />
          <Select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            options={[{ value: '', label: 'All categories' }, ...CATEGORIES]}
            className="sm:w-52"
          />
        </div>

        <div className="mt-4">
          {vocabulary.loading ? (
            <SkeletonRows rows={4} />
          ) : vocabulary.error ? (
            <ErrorState message={vocabulary.error} onRetry={vocabulary.reload} />
          ) : (vocabulary.data?.length ?? 0) === 0 ? (
            <EmptyState
              title={search || category ? 'No matching entries' : 'No vocabulary yet'}
              description="Add your name, your college, project names or jargon. Example: word “naresh”, preferred spelling “Naresh”, category “Personal name”."
              action={
                <Button size="sm" onClick={openCreate} icon={<Plus className="h-3.5 w-3.5" />}>
                  Add your first word
                </Button>
              }
            />
          ) : (
            <div className="space-y-5">
              {grouped.map(([group, entries]) => (
                <div key={group}>
                  <div className="mb-2 flex items-center gap-2">
                    <h3 className="text-[11px] font-medium uppercase tracking-wider text-ink-faint">
                      {CATEGORIES.find((c) => c.value === group)?.label ?? group}
                    </h3>
                    <span className="text-[10px] text-ink-faint">({entries.length})</span>
                  </div>
                  <ul className="space-y-2">
                    {entries.map((entry) => (
                      <li
                        key={entry.id}
                        className="flex flex-wrap items-center gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="flex flex-wrap items-center gap-2 text-sm text-ink">
                            <span className="font-mono text-ink-faint">{entry.word}</span>
                            <span className="text-ink-faint">→</span>
                            <span className="font-medium">{entry.preferred_spelling}</span>
                          </p>
                          <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-[11px] text-ink-faint">
                            <span>{LANGUAGE_META[entry.language_code]?.name ?? entry.language_code}</span>
                            {entry.pronunciation_hint && <span>· {entry.pronunciation_hint}</span>}
                            <span>· weight {entry.weight}</span>
                            <span>· used {entry.usage_count}×</span>
                            <span>· {formatRelative(entry.created_at)}</span>
                          </p>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Badge tone={entry.source === 'correction' ? 'info' : 'neutral'}>{entry.source}</Badge>
                          <Button size="sm" variant="subtle" onClick={() => toggleActive(entry)}>
                            {entry.is_active ? 'Pause' : 'Activate'}
                          </Button>
                          <Button size="sm" variant="subtle" onClick={() => openEdit(entry)} aria-label="Edit entry">
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button size="sm" variant="subtle" onClick={() => remove(entry)} aria-label="Delete entry">
                            <Trash2 className="h-3.5 w-3.5 text-red-300" />
                          </Button>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader title="How these words are used" />
        <ul className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <li>
            <span className="text-ink">Keyterm prompting:</span> up to 50 approved terms are sent with
            each request, biasing the decoder before it produces text.
          </li>
          <li>
            <span className="text-ink">Guarded correction:</span> near-miss tokens are mapped to your
            preferred spelling only when the phonetic distance is small and the token is not
            acoustically clear (confidence below 0.85).
          </li>
          <li>
            <span className="text-ink">Consent:</span> corrections are never added automatically — an
            entry exists only because you created or approved it.
          </li>
        </ul>
      </Card>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? 'Edit vocabulary entry' : 'Add vocabulary entry'}
        footer={
          <>
            <Button variant="ghost" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={submit} loading={saving}>
              {editing ? 'Save changes' : 'Add entry'}
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <Input
            label="Word as spoken"
            value={form.word}
            onChange={(e) => setForm({ ...form, word: e.target.value })}
            placeholder="naresh"
            hint="What the model tends to output."
          />
          <Input
            label="Preferred spelling"
            value={form.preferred_spelling}
            onChange={(e) => setForm({ ...form, preferred_spelling: e.target.value })}
            placeholder="Naresh"
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <Select
              label="Category"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              options={CATEGORIES}
            />
            <Select
              label="Language"
              value={form.language_code}
              onChange={(e) => setForm({ ...form, language_code: e.target.value })}
              options={Object.entries(LANGUAGE_META).map(([code, meta]) => ({
                value: code,
                label: `${meta.name} (${code})`,
              }))}
            />
          </div>
          <Input
            label="Pronunciation hint (optional)"
            value={form.pronunciation_hint}
            onChange={(e) => setForm({ ...form, pronunciation_hint: e.target.value })}
            placeholder="nuh-RESH"
          />
          <div>
            <label className="label" htmlFor="weight">
              Weight · {form.weight}
            </label>
            <input
              id="weight"
              type="range"
              min={0}
              max={5}
              step={0.5}
              value={form.weight}
              onChange={(e) => setForm({ ...form, weight: Number(e.target.value) })}
              className="w-full accent-primary"
            />
            <p className="mt-1 text-[11px] text-ink-faint">Higher weight = stronger preference when terms compete.</p>
          </div>
        </div>
      </Modal>

      <Modal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="Import vocabulary"
        footer={
          <>
            <Button variant="ghost" onClick={() => setImportOpen(false)}>
              Cancel
            </Button>
            <Button onClick={runImport}>Import</Button>
          </>
        }
      >
        <p className="text-xs text-ink-muted">
          Paste a JSON array. Fields: <span className="font-mono">word</span>,{' '}
          <span className="font-mono">preferred_spelling</span>, optional{' '}
          <span className="font-mono">category</span>, <span className="font-mono">language_code</span>,{' '}
          <span className="font-mono">pronunciation_hint</span>, <span className="font-mono">weight</span>.
        </p>
        <textarea
          value={importText}
          onChange={(e) => setImportText(e.target.value)}
          rows={8}
          placeholder={'[{"word":"cit","preferred_spelling":"CIT","category":"acronym","language_code":"en-IN"}]'}
          className="input mt-3 font-mono text-xs"
        />
      </Modal>
    </div>
  )
}
