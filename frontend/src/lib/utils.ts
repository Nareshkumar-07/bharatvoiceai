import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function formatRelative(iso?: string): string {
  if (!iso) return '—'
  const date = new Date(iso)
  const diff = Date.now() - date.getTime()
  const mins = Math.round(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  if (days < 7) return `${days}d ago`
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function formatDate(iso?: string): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function percent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${(value * 100).toFixed(digits)}%`
}

export function downloadText(filename: string, text: string) {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // clipboard API needs a secure context; fall back to a hidden textarea
    try {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(ta)
      return ok
    } catch {
      return false
    }
  }
}

export const LANGUAGE_META: Record<string, { name: string; native: string; script: string }> = {
  'ta-IN': { name: 'Tamil', native: 'தமிழ்', script: 'Tamil' },
  'hi-IN': { name: 'Hindi', native: 'हिन्दी', script: 'Devanagari' },
  'te-IN': { name: 'Telugu', native: 'తెలుగు', script: 'Telugu' },
  'ml-IN': { name: 'Malayalam', native: 'മലയാളം', script: 'Malayalam' },
  'kn-IN': { name: 'Kannada', native: 'ಕನ್ನಡ', script: 'Kannada' },
  'bn-IN': { name: 'Bengali', native: 'বাংলা', script: 'Bengali' },
  'mr-IN': { name: 'Marathi', native: 'मराठी', script: 'Devanagari' },
  'gu-IN': { name: 'Gujarati', native: 'ગુજરાતી', script: 'Gujarati' },
  'pa-IN': { name: 'Punjabi', native: 'ਪੰਜਾਬੀ', script: 'Gurmukhi' },
  'or-IN': { name: 'Odia', native: 'ଓଡ଼ିଆ', script: 'Odia' },
  'as-IN': { name: 'Assamese', native: 'অসমীয়া', script: 'Bengali' },
  'ur-IN': { name: 'Urdu', native: 'اردو', script: 'Arabic' },
  'en-IN': { name: 'English', native: 'English', script: 'Latin' },
}

export function languageName(code?: string | null): string {
  if (!code) return 'Unknown'
  return LANGUAGE_META[code]?.name ?? code
}

export function languageNative(code?: string | null): string {
  if (!code) return ''
  return LANGUAGE_META[code]?.native ?? ''
}

export const MODE_LABELS: Record<string, string> = {
  transcribe: 'Native script',
  codemix: 'Code-mixed',
  translit: 'Romanised',
  translate: 'English translation',
  verbatim: 'Verbatim',
}

export const CONTEXT_LABELS: Record<string, string> = {
  general: 'General conversation',
  email: 'Professional email',
  whatsapp: 'Casual message',
  notes: 'College notes',
  academic: 'Academic writing',
  technical: 'Technical documentation',
  code: 'Programming dictation',
}

export function greeting(): string {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}
