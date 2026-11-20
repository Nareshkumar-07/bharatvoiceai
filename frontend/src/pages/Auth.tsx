import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { AlertCircle, ArrowRight, Check, Eye, EyeOff, Lock, Mail, User as UserIcon } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { api } from '@/services/api'
import { BrandMark } from '@/components/layout/Sidebar'
import { Badge } from '@/components/ui/Badge'

type Mode = 'login' | 'signup'

export default function Auth() {
  const [params, setParams] = useSearchParams()
  const mode = (params.get('mode') === 'signup' ? 'signup' : 'login') as Mode
  const navigate = useNavigate()
  const { login, register, user } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [forgotOpen, setForgotOpen] = useState(false)
  const [forgotEmail, setForgotEmail] = useState('')
  const [forgotSent, setForgotSent] = useState<string | null>(null)

  useEffect(() => {
    if (user) navigate('/app', { replace: true })
  }, [user, navigate])

  const validate = () => {
    const errors: Record<string, string> = {}
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = 'Enter a valid email address'
    if (password.length < 8) errors.password = 'Password must be at least 8 characters'
    if (mode === 'signup' && fullName.trim().length < 2) errors.fullName = 'Tell us your name'
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    if (!validate()) return
    setSubmitting(true)
    try {
      if (mode === 'signup') await register(email.trim(), password, fullName.trim())
      else await login(email.trim(), password)
      navigate('/app', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setSubmitting(false)
    }
  }

  const sendReset = async () => {
    try {
      const res = await api.forgotPassword(forgotEmail.trim())
      setForgotSent(res.message)
    } catch (err) {
      setForgotSent(err instanceof Error ? err.message : 'Could not send the request')
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* ---------------- left: form ---------------- */}
      <div className="flex flex-col justify-center px-5 py-10 sm:px-10 lg:px-16">
        <div className="mx-auto w-full max-w-md">
          <Link to="/" className="inline-block">
            <BrandMark />
          </Link>

          <div className="mt-10">
            <h1 className="text-2xl font-semibold tracking-tight text-ink">
              {mode === 'login' ? 'Welcome back' : 'Create your account'}
            </h1>
            <p className="mt-2 text-sm text-ink-muted">
              {mode === 'login'
                ? 'Sign in to your voice workspace.'
                : 'Start dictating in any Indian language in under a minute.'}
            </p>
          </div>

          <form onSubmit={submit} className="mt-8 space-y-4" noValidate>
            {mode === 'signup' && (
              <Input
                label="Full name"
                name="fullName"
                autoComplete="name"
                placeholder="Naresh Kumar"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                error={fieldErrors.fullName}
                icon={<UserIcon className="h-4 w-4" />}
              />
            )}
            <Input
              label="Email"
              name="email"
              type="email"
              autoComplete="email"
              placeholder="you@college.edu"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={fieldErrors.email}
              icon={<Mail className="h-4 w-4" />}
            />
            <Input
              label="Password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              placeholder="At least 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={fieldErrors.password}
              icon={<Lock className="h-4 w-4" />}
              trailing={
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  className="rounded-md p-1.5 text-ink-faint hover:text-ink"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              }
            />

            {mode === 'login' && (
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => {
                    setForgotEmail(email)
                    setForgotOpen(true)
                  }}
                  className="text-xs text-ink-muted hover:text-primary-light"
                >
                  Forgot password?
                </button>
              </div>
            )}

            {error && (
              <div className="flex items-start gap-2 rounded-xl border border-red-400/25 bg-red-400/10 px-3 py-2.5 text-xs text-red-200">
                <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <Button type="submit" className="w-full" loading={submitting} iconRight={<ArrowRight className="h-4 w-4" />}>
              {mode === 'login' ? 'Sign in' : 'Create account'}
            </Button>
          </form>

          <div className="my-6 flex items-center gap-3">
            <div className="hairline flex-1" />
            <span className="text-[10px] uppercase tracking-wider text-ink-faint">or</span>
            <div className="hairline flex-1" />
          </div>

          <button
            type="button"
            onClick={() =>
              setError(
                'Google sign-in is not configured in this deployment. The backend exposes the OAuth-ready structure (oauth_provider / oauth_subject on users); set GOOGLE_CLIENT_ID and enable the route to turn it on.',
              )
            }
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2.5 text-sm text-ink hover:border-white/20"
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden>
              <path fill="#EA4335" d="M12 10.2v3.9h5.5c-.24 1.4-1.7 4.2-5.5 4.2A6.3 6.3 0 1 1 16.1 7l2.7-2.6A9.9 9.9 0 0 0 12 2a10 10 0 1 0 0 20c5.8 0 9.6-4 9.6-9.7 0-.7-.1-1.2-.2-1.7H12z" />
            </svg>
            Continue with Google
          </button>

          <p className="mt-8 text-center text-xs text-ink-muted">
            {mode === 'login' ? (
              <>
                New here?{' '}
                <button className="font-medium text-primary-light hover:underline" onClick={() => setParams({ mode: 'signup' })}>
                  Create an account
                </button>
              </>
            ) : (
              <>
                Already have an account?{' '}
                <button className="font-medium text-primary-light hover:underline" onClick={() => setParams({ mode: 'login' })}>
                  Sign in
                </button>
              </>
            )}
          </p>
        </div>
      </div>

      {/* ---------------- right: visual ---------------- */}
      <div className="relative hidden overflow-hidden border-l border-white/[0.06] lg:block">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(139,92,246,0.22),transparent_55%),radial-gradient(circle_at_75%_75%,rgba(6,182,212,0.16),transparent_55%)]" />
        <div className="relative flex h-full flex-col justify-center px-12">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7 }}
            className="max-w-md"
          >
            <Badge tone="demo">Saaras v4 · adaptive routing</Badge>
            <h2 className="mt-5 text-3xl font-semibold leading-tight tracking-tight">
              &ldquo;Bro, inniku college ku late ah varuven because traffic romba jasthi.&rdquo;
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-ink-muted">
              One sentence, two languages, zero setup. BharatVoice transcribes it, labels each
              segment, and can render it in Tamil script, romanised Tamil or professional English.
            </p>

            <div className="mt-8 space-y-3">
              {[
                ['Native script', 'தமிழ்', 'bro, இன்னைக்கு காலேஜுக்கு லேட் ஆ வருவேன்'],
                ['Romanised', 'translit', 'bro, inniku college ku late ah varuven'],
                ['English', 'translate', 'Bro, I will be late to college today.'],
              ].map(([label, tag, text]) => (
                <div key={label} className="glass p-3.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-medium uppercase tracking-wider text-ink-faint">{label}</span>
                    <span className="rounded-md border border-white/10 px-1.5 py-0.5 font-mono text-[10px] text-ink-faint">{tag}</span>
                  </div>
                  <p className="indic mt-1.5 text-sm text-ink">{text}</p>
                </div>
              ))}
            </div>

            <div className="mt-6 flex items-center gap-2 text-[11px] text-ink-faint">
              <Check className="h-3.5 w-3.5 text-emerald-400" />
              Illustrative example — the app shows real engine output with its source labelled.
            </div>
          </motion.div>
        </div>
      </div>

      <Modal
        open={forgotOpen}
        onClose={() => {
          setForgotOpen(false)
          setForgotSent(null)
        }}
        title="Reset your password"
        footer={
          <>
            <Button variant="ghost" onClick={() => setForgotOpen(false)}>
              Close
            </Button>
            <Button onClick={sendReset} disabled={!forgotEmail}>Send reset link</Button>
          </>
        }
      >
        <p className="text-sm text-ink-muted">
          Enter your account email. For security we return the same response whether or not the
          account exists.
        </p>
        <div className="mt-4">
          <Input
            label="Email"
            type="email"
            value={forgotEmail}
            onChange={(e) => setForgotEmail(e.target.value)}
            placeholder="you@college.edu"
          />
        </div>
        {forgotSent && (
          <p className="mt-4 rounded-lg border border-accent/25 bg-accent/10 px-3 py-2 text-xs text-accent-light">
            {forgotSent}
          </p>
        )}
      </Modal>
    </div>
  )
}
