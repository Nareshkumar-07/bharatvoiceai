import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowRight,
  AudioLines,
  BrainCircuit,
  Check,
  Cpu,
  Fingerprint,
  Gauge,
  Languages as LanguagesIcon,
  Lock,
  Mic,
  ShieldCheck,
  Sparkles,
  Split,
  Wand2,
} from 'lucide-react'
import { LanguageOrbit } from '@/components/landing/LanguageOrbit'
import { Reveal } from '@/animations/Reveal'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { LANGUAGE_META } from '@/lib/utils'

const WHY = [
  {
    icon: Split,
    title: 'Built for code-mixed speech',
    body: 'Indians switch languages mid-sentence. BharatVoice detects the switch per token instead of forcing one language for the whole utterance.',
  },
  {
    icon: Gauge,
    title: 'Adaptive model routing',
    body: 'A confidence-guided router retries only the uncertain parts of an utterance with a second model, so accuracy improves without paying for every model on every request.',
  },
  {
    icon: Fingerprint,
    title: 'Learns your words, with consent',
    body: 'Names, places and technical terms you approve are used as keyterms and spelling rules. Nothing is trained on your audio without you saying yes.',
  },
  {
    icon: Lock,
    title: 'Privacy as a default',
    body: 'Audio is discarded after transcription unless you opt into retention. You can delete every stored artefact from Settings in one action.',
  },
]

const STEPS = [
  {
    icon: AudioLines,
    title: 'Capture',
    body: 'The browser captures mono 16-bit PCM at 16 kHz through an AudioWorklet and streams it over a WebSocket. The waveform you see is your actual microphone amplitude.',
  },
  {
    icon: LanguagesIcon,
    title: 'Detect',
    body: 'Saaras v4 detects the language of the audio. Our code-switch module then labels each recognised token by script and lexicon, marking anything ambiguous as uncertain rather than guessing.',
  },
  {
    icon: BrainCircuit,
    title: 'Route',
    body: 'If confidence is low, the router re-runs only the uncertain segments with an alternative model and fuses the hypotheses. Every decision is logged in a trace you can read.',
  },
  {
    icon: Wand2,
    title: 'Adapt',
    body: 'Approved vocabulary is applied with a guard: acoustically clear speech is never rewritten. Then the output is rendered in native script, romanised or translated.',
  },
]

const RESEARCH = [
  {
    tag: 'Novelty 1',
    title: 'Confidence-guided adaptive ASR routing',
    body: 'Primary model → calibrated confidence → selective alternative ASR → hypothesis fusion. Thresholds are configurable and must be calibrated on your own evaluation data; the defaults are engineering starting points, not validated constants.',
  },
  {
    tag: 'Novelty 2',
    title: 'Fine-grained code-switch detection',
    body: 'Per-token language attribution with explicit uncertainty. A romanised Tamil word is never reported as English just because it uses Latin letters.',
  },
  {
    tag: 'Novelty 3',
    title: 'User-approved vocabulary adaptation',
    body: 'Keyterm prompting plus guarded spelling correction. This is a dictionary and a decoder hint — not acoustic fine-tuning, and we do not claim otherwise.',
  },
  {
    tag: 'Novelty 4',
    title: 'Context-aware output',
    body: 'Email, notes, technical and code profiles reshape punctuation and casing without inventing content. Model-backed rewriting is an optional plug-in, labelled when used.',
  },
]

const PLANS = [
  {
    name: 'Personal',
    price: 'Free',
    note: 'Bring your own Sarvam key',
    features: ['All 13 languages', 'Code-switch detection', 'Vocabulary (100 entries)', 'History & analytics', 'Local Whisper fallback'],
    cta: 'Start free',
  },
  {
    name: 'Studio',
    price: '₹499',
    note: 'per user / month',
    features: ['Everything in Personal', 'Adaptive routing + fusion', 'Unlimited vocabulary', 'Translation & transliteration', 'Evaluation harness'],
    cta: 'Start free trial',
    highlight: true,
  },
  {
    name: 'Institution',
    price: 'Talk to us',
    note: 'colleges & enterprises',
    features: ['On-premise deployment', 'Local-only inference mode', 'Custom language packs', 'SSO-ready architecture', 'Priority support'],
    cta: 'Contact us',
  },
]

export default function Landing() {
  const navigate = useNavigate()

  return (
    <div className="relative">
      {/* ---------------- hero ---------------- */}
      <section className="relative overflow-hidden px-5 pb-16 pt-14 sm:pt-20">
        <div className="mx-auto grid max-w-7xl items-center gap-12 lg:grid-cols-[1.05fr_0.95fr]">
          <div>
            <div className="fade-up inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[11px] text-ink-muted">
              <Sparkles className="h-3 w-3 text-primary-light" />
              Saaras v4 · 13 Indian languages · code-mixed by design
            </div>

            <h1
              className="fade-up mt-6 text-balance text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl"
              style={{ animationDelay: '0.05s' }}
            >
              <span className="gradient-text">Speak Naturally.</span>
              <br />
              Let AI Understand
              <br />
              Every Word.
            </h1>

            <p
              className="fade-up mt-5 max-w-xl text-base leading-relaxed text-ink-muted"
              style={{ animationDelay: '0.12s' }}
            >
              An adaptive multilingual voice intelligence platform built for India&apos;s linguistic
              diversity — Tamil, Hindi, Telugu, Malayalam, Kannada, Bengali, Marathi, Gujarati,
              Punjabi, Odia, Assamese, Urdu and English, in the same sentence.
            </p>

            <div className="fade-up mt-8 flex flex-wrap items-center gap-3" style={{ animationDelay: '0.18s' }}>
              <Button size="lg" icon={<Mic className="h-4 w-4" />} onClick={() => navigate('/auth?mode=signup')}>
                Start Speaking
              </Button>
              <Button
                size="lg"
                variant="ghost"
                iconRight={<ArrowRight className="h-4 w-4" />}
                onClick={() => document.getElementById('technology')?.scrollIntoView({ behavior: 'smooth' })}
              >
                Explore Technology
              </Button>
            </div>

            <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-ink-faint">
              {['No fabricated transcripts', 'Audio discarded by default', 'CPU-friendly'].map((item) => (
                <span key={item} className="inline-flex items-center gap-1.5">
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                  {item}
                </span>
              ))}
            </div>
          </div>

          <div className="relative">
            <LanguageOrbit />
          </div>
        </div>
      </section>

      {/* ---------------- why ---------------- */}
      <section id="why" className="px-5 py-16">
        <div className="mx-auto max-w-7xl">
          <Reveal>
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-primary-light">Why BharatVoice</p>
            <h2 className="mt-3 max-w-2xl text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
              Voice typing that stops pretending India speaks one language at a time
            </h2>
          </Reveal>

          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {WHY.map((item, i) => (
              <Reveal key={item.title} delay={i * 0.06}>
                <Card className="h-full card-hover">
                  <span className="grid h-10 w-10 place-items-center rounded-xl border border-primary/25 bg-primary/10 text-primary-light">
                    <item.icon className="h-4.5 w-4.5" style={{ height: 18, width: 18 }} />
                  </span>
                  <h3 className="mt-4 text-sm font-semibold text-ink">{item.title}</h3>
                  <p className="mt-2 text-xs leading-relaxed text-ink-muted">{item.body}</p>
                </Card>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------- languages ---------------- */}
      <section id="languages" className="px-5 py-16">
        <div className="mx-auto max-w-7xl">
          <Reveal>
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.2em] text-accent-light">Supported languages</p>
                <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">13 languages, one microphone</h2>
                <p className="mt-3 max-w-xl text-sm text-ink-muted">
                  Recognition coverage comes from the configured model, not from marketing. The
                  workspace shows exactly which engine is answering every request.
                </p>
              </div>
              <Badge tone="info">Saaras v4 coverage</Badge>
            </div>
          </Reveal>

          <div className="mt-10 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {Object.entries(LANGUAGE_META).map(([code, meta], i) => (
              <Reveal key={code} delay={i * 0.03}>
                <div className="glass card-hover flex items-center justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <p className="indic truncate text-base font-semibold text-ink">{meta.native}</p>
                    <p className="mt-0.5 truncate text-[11px] text-ink-faint">
                      {meta.name} · {meta.script}
                    </p>
                  </div>
                  <span className="shrink-0 rounded-md border border-white/10 px-1.5 py-0.5 font-mono text-[10px] text-ink-faint">
                    {code}
                  </span>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------- technology ---------------- */}
      <section id="technology" className="px-5 py-16">
        <div className="mx-auto max-w-7xl">
          <Reveal>
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-primary-light">Intelligent recognition</p>
            <h2 className="mt-3 max-w-3xl text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
              Four stages, each one inspectable
            </h2>
          </Reveal>

          <div className="mt-10 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="grid gap-3 sm:grid-cols-2">
              {STEPS.map((step, i) => (
                <Reveal key={step.title} delay={i * 0.05}>
                  <Card className="h-full">
                    <div className="flex items-center gap-2">
                      <span className="grid h-8 w-8 place-items-center rounded-lg border border-accent/25 bg-accent/10 text-accent-light">
                        <step.icon className="h-4 w-4" />
                      </span>
                      <span className="font-mono text-[11px] text-ink-faint">0{i + 1}</span>
                      <h3 className="text-sm font-semibold text-ink">{step.title}</h3>
                    </div>
                    <p className="mt-3 text-xs leading-relaxed text-ink-muted">{step.body}</p>
                  </Card>
                </Reveal>
              ))}
            </div>

            <Reveal delay={0.1}>
              <Card className="h-full">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-ink">Code-switch timeline</h3>
                  <Badge>illustrative example</Badge>
                </div>
                <p className="mt-3 rounded-lg border border-white/10 bg-black/25 p-3 text-sm leading-relaxed text-ink">
                  &ldquo;Tomorrow meeting <span className="text-primary-light">ku</span> presentation ready{' '}
                  <span className="text-primary-light">pannidu</span>&rdquo;
                </p>
                <div className="mt-4 space-y-2">
                  {[
                    ['Tomorrow', 'English', 'English lexicon', 'en'],
                    ['meeting', 'English', 'English lexicon', 'en'],
                    ['ku', 'Tamil', 'romanised marker', 'ta'],
                    ['presentation', 'English', 'English lexicon', 'en'],
                    ['ready', 'English', 'English lexicon', 'en'],
                    ['pannidu', 'Tamil', 'romanised marker', 'ta'],
                  ].map(([token, language, evidence, lang]) => (
                    <div key={token} className="flex items-center gap-3 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2">
                      <span className="w-24 shrink-0 font-mono text-xs text-ink">{token}</span>
                      <span
                        className={
                          lang === 'en'
                            ? 'rounded-md border border-accent/30 bg-accent/10 px-1.5 py-0.5 text-[10px] text-accent-light'
                            : 'rounded-md border border-primary/30 bg-primary/10 px-1.5 py-0.5 text-[10px] text-primary-light'
                        }
                      >
                        {language}
                      </span>
                      <span className="ml-auto text-[10px] text-ink-faint">{evidence}</span>
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-[11px] leading-relaxed text-ink-faint">
                  Token-level attribution is a script + lexicon heuristic over recognised text.
                  It is labelled as such in the product — it is not an acoustic language-ID score.
                </p>
              </Card>
            </Reveal>
          </div>
        </div>
      </section>

      {/* ---------------- research ---------------- */}
      <section id="research" className="px-5 py-16">
        <div className="mx-auto max-w-7xl">
          <Reveal>
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-accent-light">Research innovation</p>
            <h2 className="mt-3 max-w-3xl text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
              Four modules that are code, not claims
            </h2>
            <p className="mt-3 max-w-2xl text-sm text-ink-muted">
              Each module below ships in <span className="font-mono text-xs text-ink">ai_engine/intelligence/</span>{' '}
              with unit tests. Where a number cannot be measured yet, the interface says so.
            </p>
          </Reveal>

          <div className="mt-10 grid gap-4 sm:grid-cols-2">
            {RESEARCH.map((item, i) => (
              <Reveal key={item.title} delay={i * 0.05}>
                <Card className="h-full card-hover">
                  <Badge tone="info">{item.tag}</Badge>
                  <h3 className="mt-3 text-sm font-semibold text-ink">{item.title}</h3>
                  <p className="mt-2 text-xs leading-relaxed text-ink-muted">{item.body}</p>
                </Card>
              </Reveal>
            ))}
          </div>

          <Reveal delay={0.1}>
            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              {[
                { icon: ShieldCheck, title: 'Privacy-first architecture', body: 'Retention is opt-in, deletion is one click, and the UI states whether processing was local, on our server or at a provider.' },
                { icon: Cpu, title: 'CPU or GPU', body: 'Sarvam runs remotely; Whisper and IndicConformer run locally on CPU with int8 quantisation, or on GPU with one env flag.' },
                { icon: Split, title: 'Provider-agnostic', body: 'The frontend never names a provider. Swapping Saaras for another engine is a registry change in the backend.' },
              ].map((item) => (
                <Card key={item.title}>
                  <item.icon className="h-5 w-5 text-primary-light" />
                  <h3 className="mt-3 text-sm font-semibold text-ink">{item.title}</h3>
                  <p className="mt-2 text-xs leading-relaxed text-ink-muted">{item.body}</p>
                </Card>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* ---------------- pricing ---------------- */}
      <section id="pricing" className="px-5 py-16">
        <div className="mx-auto max-w-7xl">
          <Reveal>
            <div className="text-center">
              <p className="text-xs font-medium uppercase tracking-[0.2em] text-primary-light">Pricing</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">Start free, scale when it earns it</h2>
              <p className="mx-auto mt-3 max-w-xl text-sm text-ink-muted">
                You bring the Sarvam API key, so provider cost stays visible and yours. The
                self-hosted app has no per-seat fee.
              </p>
            </div>
          </Reveal>

          <div className="mt-10 grid gap-4 lg:grid-cols-3">
            {PLANS.map((plan, i) => (
              <Reveal key={plan.name} delay={i * 0.06}>
                <Card
                  className={
                    plan.highlight
                      ? 'relative h-full border-primary/40 bg-gradient-to-b from-primary/[0.12] to-transparent'
                      : 'h-full'
                  }
                >
                  {plan.highlight && (
                    <span className="absolute right-4 top-4 rounded-full bg-primary/20 px-2 py-0.5 text-[10px] font-medium text-primary-light">
                      Most popular
                    </span>
                  )}
                  <h3 className="text-sm font-semibold text-ink">{plan.name}</h3>
                  <p className="mt-3 text-3xl font-semibold tracking-tight text-ink">{plan.price}</p>
                  <p className="mt-1 text-xs text-ink-faint">{plan.note}</p>
                  <ul className="mt-5 space-y-2">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-start gap-2 text-xs text-ink-muted">
                        <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Button
                    className="mt-6 w-full"
                    variant={plan.highlight ? 'primary' : 'ghost'}
                    onClick={() => navigate('/auth?mode=signup')}
                  >
                    {plan.cta}
                  </Button>
                </Card>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------- CTA ---------------- */}
      <section className="px-5 pb-20">
        <div className="mx-auto max-w-5xl">
          <Reveal>
            <div className="gradient-border glass-strong relative overflow-hidden p-10 text-center">
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(139,92,246,0.25),transparent_60%)]" />
              <h2 className="relative text-balance text-3xl font-semibold tracking-tight">
                Your voice. Every Indian language. One intelligence.
              </h2>
              <p className="relative mx-auto mt-3 max-w-xl text-sm text-ink-muted">
                Create an account and dictate your first sentence in under a minute.
              </p>
              <div className="relative mt-7 flex flex-wrap justify-center gap-3">
                <Button size="lg" onClick={() => navigate('/auth?mode=signup')}>
                  Create free account
                </Button>
                <Link to="/app/workspace">
                  <Button size="lg" variant="ghost">
                    Open the workspace
                  </Button>
                </Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>
    </div>
  )
}
