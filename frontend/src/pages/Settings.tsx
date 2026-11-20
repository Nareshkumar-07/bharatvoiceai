import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  Check,
  Download,
  Keyboard,
  Monitor,
  Save,
  ShieldCheck,
  Trash2,
  User as UserIcon,
  Volume2,
} from 'lucide-react'
import { useApiResource } from '@/hooks/useApiResource'
import { api } from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import { useLocalStorage } from '@/hooks/useLocalStorage'
import { useToast } from '@/components/ui/Toast'
import { Card, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input, Select, Toggle } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { ErrorState, LoadingState } from '@/components/ui/States'
import { LANGUAGE_META, MODE_LABELS } from '@/lib/utils'
import type { Preferences } from '@/types'

export default function Settings() {
  const { user, logout, refreshUser } = useAuth()
  const prefs = useApiResource(() => api.settings(), [])
  const engine = useApiResource(() => api.engineStatus(), [])
  const [form, setForm] = useState<Preferences | null>(null)
  const [fullName, setFullName] = useState(user?.full_name ?? '')
  const [saving, setSaving] = useState(false)
  const [reducedMotion, setReducedMotion] = useLocalStorage('bharatvoice.reducedMotion', false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const { push } = useToast()

  useEffect(() => {
    if (prefs.data) setForm(prefs.data)
  }, [prefs.data])

  useEffect(() => {
    document.documentElement.dataset.reducedMotion = String(reducedMotion)
  }, [reducedMotion])

  const save = async () => {
    if (!form) return
    setSaving(true)
    try {
      const updated = await api.updateSettings(form)
      setForm(updated)
      push('Settings saved', 'success')
    } catch (err) {
      push(err instanceof Error ? err.message : 'Could not save settings', 'error')
    } finally {
      setSaving(false)
    }
  }

  const saveProfile = async () => {
    try {
      await api.updateProfile(fullName)
      await refreshUser()
      push('Profile updated', 'success')
    } catch (err) {
      push(err instanceof Error ? err.message : 'Could not update profile', 'error')
    }
  }

  const deleteEverything = async () => {
    try {
      const res = await api.deleteAllData()
      push(`Deleted ${Object.values(res.deleted).reduce((a, b) => a + b, 0)} records`, 'success')
      setDeleteOpen(false)
    } catch (err) {
      push(err instanceof Error ? err.message : 'Delete failed', 'error')
    }
  }

  if (prefs.loading || !form) return <LoadingState label="Loading your settings…" />
  if (prefs.error) return <ErrorState message={prefs.error} onRetry={prefs.reload} />

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Settings</h1>
        <p className="mt-1 text-sm text-ink-muted">Preferences, privacy controls and keyboard shortcuts.</p>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader title="Profile" description={user?.email} icon={<UserIcon className="h-4 w-4" />} />
          <div className="space-y-3">
            <Input label="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
            <div className="flex justify-end">
              <Button size="sm" onClick={saveProfile} disabled={fullName === user?.full_name}>
                Save profile
              </Button>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader title="Recognition defaults" description="Applied to new recordings." icon={<Volume2 className="h-4 w-4" />} />
          <div className="space-y-3">
            <Select
              label="Default output mode"
              value={form.default_output_mode}
              onChange={(e) => setForm({ ...form, default_output_mode: e.target.value as Preferences['default_output_mode'] })}
              options={Object.entries(MODE_LABELS).map(([value, label]) => ({ value, label }))}
            />
            <Select
              label="Default context"
              value={form.default_context}
              onChange={(e) => setForm({ ...form, default_context: e.target.value as Preferences['default_context'] })}
              options={[
                { value: 'general', label: 'General conversation' },
                { value: 'email', label: 'Professional email' },
                { value: 'whatsapp', label: 'Casual message' },
                { value: 'notes', label: 'College notes' },
                { value: 'academic', label: 'Academic writing' },
                { value: 'technical', label: 'Technical documentation' },
                { value: 'code', label: 'Programming dictation' },
              ]}
            />
            <Select
              label="Audio quality"
              value={form.audio_quality}
              onChange={(e) => setForm({ ...form, audio_quality: e.target.value as Preferences['audio_quality'] })}
              options={[
                { value: 'low', label: 'Low (8 kHz, smallest upload)' },
                { value: 'medium', label: 'Medium (16 kHz)' },
                { value: 'high', label: 'High (16 kHz + normalisation)' },
              ]}
            />
            <div className="divide-y divide-white/[0.06]">
              <Toggle
                label="Noise reduction"
                description="Spectral gate, or DeepFilterNet when installed."
                checked={form.noise_reduction}
                onChange={(v) => setForm({ ...form, noise_reduction: v })}
              />
              <Toggle
                label="Voice activity detection"
                description="Segment speech before recognition; drops silence from uploads."
                checked={form.vad_enabled}
                onChange={(v) => setForm({ ...form, vad_enabled: v })}
              />
              <Toggle
                label="Auto punctuation"
                description="Apply punctuation and casing rules from the context profile."
                checked={form.auto_punctuation}
                onChange={(v) => setForm({ ...form, auto_punctuation: v })}
              />
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader title="Languages" description="Preferred languages appear first in pickers." />
          <div className="flex flex-wrap gap-2">
            {Object.entries(LANGUAGE_META).map(([code, meta]) => {
              const active = form.preferred_languages.includes(code)
              return (
                <button
                  key={code}
                  onClick={() =>
                    setForm({
                      ...form,
                      preferred_languages: active
                        ? form.preferred_languages.filter((c) => c !== code)
                        : [...form.preferred_languages, code],
                    })
                  }
                  className={
                    active
                      ? 'rounded-lg border border-primary/40 bg-primary/10 px-2.5 py-1.5 text-xs text-primary-light'
                      : 'rounded-lg border border-white/10 px-2.5 py-1.5 text-xs text-ink-muted hover:text-ink'
                  }
                >
                  {active && <Check className="mr-1 inline h-3 w-3" />}
                  {meta.native}
                </button>
              )
            })}
          </div>
        </Card>

        <Card>
          <CardHeader title="Appearance & accessibility" icon={<Monitor className="h-4 w-4" />} />
          <div className="divide-y divide-white/[0.06]">
            <Toggle
              label="Reduced motion"
              description="Turns off ambient particles, breathing microphone and scroll animations."
              checked={reducedMotion}
              onChange={setReducedMotion}
            />
            <Toggle
              label="Theme"
              description="BharatVoice ships a dark theme; light theme tokens exist but are not production-ready."
              checked={form.theme === 'dark'}
              onChange={(v) => setForm({ ...form, theme: v ? 'dark' : 'light' })}
            />
          </div>
        </Card>

        <Card>
          <CardHeader title="Privacy & retention" description="You decide what is kept." icon={<ShieldCheck className="h-4 w-4" />} />
          <div className="space-y-3">
            <Select
              label="Audio retention"
              value={form.audio_retention}
              onChange={(e) => setForm({ ...form, audio_retention: e.target.value as Preferences['audio_retention'] })}
              options={[
                { value: 'discard', label: 'Discard immediately (default)' },
                { value: '30d', label: 'Keep for 30 days' },
                { value: '90d', label: 'Keep for 90 days' },
                { value: 'keep', label: 'Keep until I delete it' },
              ]}
            />
            <Toggle
              label="Offline-first preference"
              description="Prefer locally installed models when available. Has no effect unless a local model is enabled on the backend."
              checked={form.offline_mode}
              onChange={(v) => setForm({ ...form, offline_mode: v })}
            />
            <div className="rounded-xl border border-red-400/20 bg-red-400/[0.06] p-3">
              <p className="flex items-center gap-2 text-xs font-medium text-red-200">
                <AlertTriangle className="h-3.5 w-3.5" /> Delete all my data
              </p>
              <p className="mt-1 text-[11px] leading-relaxed text-red-200/80">
                Removes every transcription, vocabulary entry, routing decision and analytics event on
                your account. This cannot be undone.
              </p>
              <Button size="sm" variant="danger" className="mt-2" icon={<Trash2 className="h-3.5 w-3.5" />} onClick={() => setDeleteOpen(true)}>
                Delete everything
              </Button>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader title="Keyboard shortcuts" description="Active in the workspace." icon={<Keyboard className="h-4 w-4" />} />
          <div className="space-y-2">
            {Object.entries(form.keyboard_shortcuts).map(([action, combo]) => (
              <div key={action} className="flex items-center justify-between rounded-lg border border-white/[0.06] px-3 py-2 text-xs">
                <span className="text-ink-muted">{action === 'toggleRecording' ? 'Start / stop recording' : 'Copy last transcript'}</span>
                <kbd className="rounded-md border border-white/15 bg-white/[0.06] px-2 py-0.5 font-mono text-[10px] text-ink">{combo}</kbd>
              </div>
            ))}
            <p className="text-[11px] leading-relaxed text-ink-faint">
              The browser tab can only receive shortcuts while it is focused. Global activation
              requires the Tauri desktop build — a web page cannot inject text into other applications.
            </p>
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader title="Deployment status" description="What this installation can actually do." />
        {engine.data ? (
          <div className="grid gap-2 sm:grid-cols-2">
            {Object.entries(engine.data.capabilities).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between rounded-lg border border-white/[0.06] px-3 py-2 text-xs">
                <span className="text-ink-muted">{key.replace(/_/g, ' ')}</span>
                <Badge tone={value ? 'success' : 'neutral'}>{value ? 'yes' : 'no'}</Badge>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-ink-faint">Status unavailable.</p>
        )}
      </Card>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button
          variant="ghost"
          icon={<Download className="h-4 w-4" />}
          onClick={() => {
            const blob = new Blob([JSON.stringify(form, null, 2)], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = 'bharatvoice-settings.json'
            a.click()
            URL.revokeObjectURL(url)
          }}
        >
          Export settings
        </Button>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={() => logout()}>
            Sign out
          </Button>
          <Button icon={<Save className="h-4 w-4" />} loading={saving} onClick={save}>
            Save settings
          </Button>
        </div>
      </div>

      <Modal
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        title="Delete all data?"
        footer={
          <>
            <Button variant="ghost" onClick={() => setDeleteOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={deleteEverything}>
              Yes, delete everything
            </Button>
          </>
        }
      >
        <p className="text-sm text-ink-muted">
          This permanently removes your transcriptions, vocabulary, routing decisions and analytics
          events. Your account itself stays active.
        </p>
      </Modal>
    </div>
  )
}
