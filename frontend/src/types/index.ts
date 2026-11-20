export type OutputMode = 'transcribe' | 'codemix' | 'translit' | 'translate' | 'verbatim'
export type ContextProfile =
  | 'general'
  | 'email'
  | 'whatsapp'
  | 'notes'
  | 'academic'
  | 'technical'
  | 'code'
export type EngineStatus = 'ok' | 'degraded' | 'demo_fixture' | 'unavailable'
export type ConfidenceSource = 'provider' | 'proxy' | 'heuristic' | null

export interface User {
  id: string
  email: string
  full_name: string
  is_demo?: boolean
  created_at?: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

export interface Language {
  code: string
  name: string
  native_name: string
  script: string
  recognition_supported: boolean
  is_active: boolean
}

export interface Segment {
  index?: number
  text: string
  language?: string | null
  language_name?: string
  language_label?: string | null
  kind?: 'matrix' | 'embedded' | 'uncertain'
  confidence?: number | null
  confidence_source?: string | null
  start_ms?: number
  end_ms?: number
  is_uncertain?: boolean
}

export interface OutputVariant {
  text: string | null
  available: boolean
  method?: string
  provider?: string
  reason?: string | null
}

export interface SpeechResult {
  id: string
  text: string
  mode: OutputMode
  primary_language: string | null
  languages: string[]
  is_code_mixed: boolean
  code_switch_count: number
  confidence: number | null
  confidence_source: ConfidenceSource
  confidence_components: Record<string, number>
  engine_status: EngineStatus
  demo: boolean
  model_used: string | null
  latency_ms: number | null
  needs_confirmation: boolean
  segments: Segment[]
  outputs: Record<string, OutputVariant>
  routing: {
    primary_model: string
    alternatives_used: string[]
    escalated: boolean
    reason: string
    trace: TraceStep[]
    policy: Record<string, unknown>
  }
  audio: {
    duration_seconds: number
    peak: number
    dbfs?: number
    retained: boolean
    vad?: Record<string, unknown>
    noise_reduction?: Record<string, unknown>
  }
  word_count: number
  duration_seconds: number
  professional_text?: string | null
  message: string | null
}

export interface TraceStep {
  step: string
  status: string
  detail: string
  at_ms?: number
  [key: string]: unknown
}

export interface Transcription {
  id: string
  title: string
  original_text: string
  native_text?: string | null
  romanized_text?: string | null
  english_text?: string | null
  professional_text?: string | null
  detected_languages: string[]
  primary_language?: string | null
  is_code_mixed: boolean
  code_switch_count: number
  duration_seconds: number
  word_count: number
  model_used?: string | null
  output_mode: OutputMode
  context_profile: string
  status: string
  engine_status: EngineStatus
  confidence?: number | null
  confidence_source?: ConfidenceSource
  latency_ms?: number | null
  audio_retained: boolean
  edit_count: number
  created_at?: string
  segments: Segment[]
}

export interface HistoryPage {
  items: Transcription[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface VocabularyEntry {
  id: string
  word: string
  preferred_spelling: string
  category: string
  language_code: string
  pronunciation_hint?: string | null
  weight: number
  is_active: boolean
  source: string
  usage_count: number
  created_at?: string
}

export interface ModelInfo {
  model_id: string
  provider: string
  available: boolean
  reason: string | null
  supports_modes: string[]
  supports_streaming: boolean
  returns_confidence: boolean
  runtime: string
  is_primary?: boolean
}

export interface EngineStatusPayload {
  primary_engine: string | null
  primary_available: boolean
  primary_unavailable_reason?: string | null
  streaming_available: boolean
  demo_mode: boolean
  models: ModelInfo[]
  translation: Record<string, { available: boolean; reason: string | null }>
  transliteration: Record<string, { available: boolean; reason: string | null }>
  usage: {
    month: string
    requests: number
    monthly_budget: number
    audio_seconds: number
    failures: number
    utilisation: number
  }
  capabilities: Record<string, boolean>
  notes: string[]
}

export interface RouterMetrics {
  decisions: number
  escalations: number
  escalation_rate: number | null
  confirmation_requests: number
  average_latency_ms: number | null
  model_usage: Record<string, number>
  predictions_logged?: number
  policy: {
    enabled: boolean
    confidence_threshold: number
    confirmation_threshold: number
    max_alternatives: number
    latency_budget_ms: number
  }
  calibration: { fitted: boolean; samples: number; note: string }
  has_data: boolean
}

export interface AnalyticsOverview {
  total_transcriptions: number
  total_words: number
  total_duration_seconds: number
  code_mixed_percentage: number
  average_correction_rate: number | null
  languages_used: number
  current_streak_days: number
  words_this_week: number
  has_data: boolean
}

export interface LanguageUsage {
  code: string
  name: string
  count: number
  words: number
  share: number
}

export interface PerformanceMetrics {
  average_latency_ms: number | null
  p95_latency_ms: number | null
  model_usage: Record<string, number>
  engine_status_breakdown: Record<string, number>
  confidence_coverage: number
  notes: string[]
}

export interface ActivityPoint {
  date?: string
  week?: string
  transcriptions: number
  words: number
}

export interface Preferences {
  preferred_languages: string[]
  default_output_mode: OutputMode
  default_context: ContextProfile
  audio_quality: 'low' | 'medium' | 'high'
  noise_reduction: boolean
  vad_enabled: boolean
  offline_mode: boolean
  auto_punctuation: boolean
  audio_retention: 'discard' | '30d' | '90d' | 'keep'
  theme: 'dark' | 'light'
  reduced_motion: boolean
  keyboard_shortcuts: Record<string, string>
}

export interface DetectResponse {
  verdict: {
    code: string | null
    name: string
    confidence: number
    method: string
    confidence_source: string
    is_reliable: boolean
    ambiguous_with: string[]
    scores: Record<string, number>
    script_mix: Record<string, number>
  }
  code_switching: {
    spans: Segment[]
    tokens: Array<{
      token: string
      language: string | null
      script: string
      confidence: number
      evidence: string
      uncertain: boolean
    }>
    primary_language: string | null
    languages: string[]
    switch_count: number
    code_mixed_ratio: number
    is_code_mixed: boolean
    uncertain_tokens: number
    method: string
  }
}
