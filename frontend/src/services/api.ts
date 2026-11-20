/**
 * Typed API client.
 *
 * The browser only ever talks to our backend. Provider keys (SARVAM_API_KEY)
 * live in the backend environment; nothing here can see or send them.
 */
import type {
  ActivityPoint,
  AnalyticsOverview,
  AuthResponse,
  DetectResponse,
  EngineStatusPayload,
  HistoryPage,
  Language,
  LanguageUsage,
  PerformanceMetrics,
  Preferences,
  RouterMetrics,
  SpeechResult,
  Transcription,
  User,
  VocabularyEntry,
} from '@/types'

const RAW_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ''
export const API_BASE = RAW_BASE.replace(/\/$/, '')
export const WS_BASE =
  (import.meta.env.VITE_WS_BASE_URL as string | undefined)?.replace(/\/$/, '') ??
  (API_BASE ? API_BASE.replace(/^http/, 'ws') : `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`)

const ACCESS_KEY = 'bharatvoice.access'
const REFRESH_KEY = 'bharatvoice.refresh'

export const tokenStore = {
  get access() {
    return localStorage.getItem(ACCESS_KEY)
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY)
  },
  set(access: string, refresh: string) {
    localStorage.setItem(ACCESS_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

export class ApiError extends Error {
  status: number
  payload: unknown
  constructor(message: string, status: number, payload?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

function messageFrom(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== 'object') return fallback
  const p = payload as Record<string, unknown>
  const msg = p.message ?? p.detail ?? p.error
  if (typeof msg === 'string') return msg
  if (msg && typeof msg === 'object' && 'message' in (msg as Record<string, unknown>)) {
    const inner = (msg as Record<string, unknown>).message
    if (typeof inner === 'string') return inner
  }
  if (Array.isArray(p.detail) && p.detail.length) {
    const first = p.detail[0] as Record<string, unknown>
    if (typeof first?.msg === 'string') return first.msg
  }
  return fallback
}

let refreshing: Promise<boolean> | null = null

async function refreshTokens(): Promise<boolean> {
  const refresh = tokenStore.refresh
  if (!refresh) return false
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refresh }),
        })
        if (!res.ok) return false
        const data = (await res.json()) as AuthResponse
        tokenStore.set(data.access_token, data.refresh_token)
        return true
      } catch {
        return false
      } finally {
        setTimeout(() => {
          refreshing = null
        }, 0)
      }
    })()
  }
  return refreshing
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  { retryOn401 = true }: { retryOn401?: boolean } = {},
): Promise<T> {
  const headers = new Headers(init.headers)
  if (!(init.body instanceof FormData) && init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const token = tokenStore.access
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers })
  } catch (err) {
    throw new ApiError(
      'Cannot reach the BharatVoice API. Is the backend running on port 8000?',
      0,
      err,
    )
  }

  if (res.status === 401 && retryOn401) {
    const ok = await refreshTokens()
    if (ok) return request<T>(path, init, { retryOn401: false })
    tokenStore.clear()
  }

  if (res.status === 204) return undefined as T

  const contentType = res.headers.get('content-type') ?? ''
  const payload = contentType.includes('application/json')
    ? await res.json().catch(() => null)
    : await res.text()

  if (!res.ok) {
    throw new ApiError(messageFrom(payload, `Request failed (${res.status})`), res.status, payload)
  }
  return payload as T
}

export const api = {
  // --- auth ---
  register: (body: { email: string; password: string; full_name?: string }) =>
    request<AuthResponse>('/api/auth/register', { method: 'POST', body: JSON.stringify(body) }),
  login: (body: { email: string; password: string }) =>
    request<AuthResponse>('/api/auth/login', { method: 'POST', body: JSON.stringify(body) }),
  me: () => request<User>('/api/auth/me'),
  logout: () => request<void>('/api/auth/logout', { method: 'POST' }),
  forgotPassword: (email: string) =>
    request<{ status: string; message: string }>('/api/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),

  // --- speech ---
  transcribe: (file: Blob, fields: Record<string, string>) => {
    const form = new FormData()
    form.append('file', file, 'recording.wav')
    Object.entries(fields).forEach(([k, v]) => form.append(k, v))
    return request<SpeechResult>('/api/speech/transcribe', { method: 'POST', body: form })
  },

  // --- languages ---
  languages: () => request<Language[]>('/api/languages'),
  detect: (text: string, base?: string) =>
    request<DetectResponse>('/api/languages/detect', {
      method: 'POST',
      body: JSON.stringify({ text, base_language: base ?? null }),
    }),
  translate: (body: { text: string; source_language?: string; target_language?: string; mode?: string }) =>
    request<{ text: string; available: boolean; method: string; reason?: string | null }>(
      '/api/languages/translate',
      { method: 'POST', body: JSON.stringify(body) },
    ),
  transliterate: (body: { text: string; source_language?: string; target_language?: string }) =>
    request<{ text: string; available: boolean; method: string; reason?: string | null }>(
      '/api/languages/transliterate',
      { method: 'POST', body: JSON.stringify(body) },
    ),

  // --- vocabulary ---
  vocabulary: (params: { search?: string; category?: string; language_code?: string } = {}) => {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => v && q.set(k, v))
    return request<VocabularyEntry[]>(`/api/vocabulary${q.toString() ? `?${q}` : ''}`)
  },
  createVocabulary: (body: Partial<VocabularyEntry>) =>
    request<VocabularyEntry>('/api/vocabulary', { method: 'POST', body: JSON.stringify(body) }),
  updateVocabulary: (id: string, body: Partial<VocabularyEntry>) =>
    request<VocabularyEntry>(`/api/vocabulary/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteVocabulary: (id: string) =>
    request<void>(`/api/vocabulary/${id}`, { method: 'DELETE' }),
  importVocabulary: (entries: Partial<VocabularyEntry>[]) =>
    request<{ created: number; skipped: number }>('/api/vocabulary/import', {
      method: 'POST',
      body: JSON.stringify({ entries }),
    }),
  exportVocabularyUrl: (fmt: 'json' | 'csv') => `${API_BASE}/api/vocabulary/export?fmt=${fmt}`,

  // --- history ---
  history: (params: Record<string, string | number | undefined> = {}) => {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== '') q.set(k, String(v))
    })
    return request<HistoryPage>(`/api/history${q.toString() ? `?${q}` : ''}`)
  },
  historyItem: (id: string) => request<Transcription>(`/api/history/${id}`),
  updateHistory: (id: string, body: Partial<Transcription>) =>
    request<Transcription>(`/api/history/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteHistory: (id: string) => request<void>(`/api/history/${id}`, { method: 'DELETE' }),
  rewrite: (id: string, profile: string) =>
    request<{ text: string; method: string; changes: string[]; profile: string }>(
      `/api/history/${id}/rewrite?profile=${encodeURIComponent(profile)}`,
      { method: 'POST' },
    ),
  generateOutput: (id: string, kind: 'native' | 'romanized' | 'english') =>
    request<{ text: string | null; available: boolean; method?: string; reason?: string | null }>(
      `/api/history/${id}/outputs/${kind}`,
      { method: 'POST' },
    ),

  // --- analytics ---
  overview: () => request<AnalyticsOverview>('/api/analytics/overview'),
  languageUsage: () => request<LanguageUsage[]>('/api/analytics/languages'),
  performance: () => request<PerformanceMetrics>('/api/analytics/performance'),
  activity: (granularity: 'day' | 'week' = 'day') =>
    request<ActivityPoint[]>(`/api/analytics/activity?granularity=${granularity}`),

  // --- ai ---
  engineStatus: () => request<EngineStatusPayload>('/api/ai/status'),
  routerMetrics: () => request<RouterMetrics>('/api/ai/router/metrics'),
  updatePolicy: (body: Record<string, number | boolean>) =>
    request<{ policy: RouterMetrics['policy'] }>('/api/ai/router/policy', {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  evaluation: () =>
    request<{
      available: boolean
      reason: string | null
      wer: number | null
      cer: number | null
      notes: string[]
    }>('/api/ai/evaluation'),

  // --- settings ---
  settings: () => request<Preferences>('/api/settings'),
  updateSettings: (body: Partial<Preferences>) =>
    request<Preferences>('/api/settings', { method: 'PUT', body: JSON.stringify(body) }),
  updateProfile: (full_name: string) =>
    request<{ id: string; email: string; full_name: string }>('/api/settings/profile', {
      method: 'PUT',
      body: JSON.stringify({ full_name }),
    }),
  deleteAllData: () =>
    request<{ deleted: Record<string, number> }>('/api/settings/data', { method: 'DELETE' }),
}

export function liveSocketUrl(token: string): string {
  return `${WS_BASE}/ws/speech/live?token=${encodeURIComponent(token)}`
}
