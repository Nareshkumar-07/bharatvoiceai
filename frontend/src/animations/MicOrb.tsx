/** The microphone control: breathing when idle, pulsing rings while recording. */
import { motion, useReducedMotion } from 'framer-motion'
import { Mic, Square, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { RecorderState } from '@/hooks/useRecorder'

interface Props {
  state: RecorderState
  level: number
  onStart: () => void
  onStop: () => void
  size?: 'md' | 'lg'
}

export function MicOrb({ state, level, onStart, onStop, size = 'lg' }: Props) {
  const reduce = useReducedMotion()
  const recording = state === 'recording'
  const busy = state === 'requesting' || state === 'stopping' || state === 'processing'
  const dimension = size === 'lg' ? 'h-40 w-40' : 'h-28 w-28'
  const inner = size === 'lg' ? 'h-24 w-24' : 'h-16 w-16'

  return (
    <div className="relative flex items-center justify-center">
      {/* reactive halo driven by real mic level */}
      <div
        className="pointer-events-none absolute rounded-full transition-all duration-100"
        style={{
          width: 220 + level * 120,
          height: 220 + level * 120,
          background:
            'radial-gradient(circle, rgba(139,92,246,0.28), rgba(6,182,212,0.10) 55%, transparent 72%)',
          opacity: recording ? 0.9 : 0.45,
        }}
      />

      {(recording || state === 'processing') &&
        !reduce &&
        [0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="absolute rounded-full border border-primary/40"
            style={{ width: 168, height: 168 }}
            initial={{ scale: 0.9, opacity: 0.5 }}
            animate={{ scale: 1.6, opacity: 0 }}
            transition={{ duration: 2.6, repeat: Infinity, delay: i * 0.85, ease: 'easeOut' }}
          />
        ))}

      <motion.button
        type="button"
        onClick={recording ? onStop : onStart}
        disabled={busy}
        aria-label={recording ? 'Stop recording' : 'Start recording'}
        aria-pressed={recording}
        whileHover={reduce ? undefined : { scale: 1.03 }}
        whileTap={reduce ? undefined : { scale: 0.97 }}
        animate={
          reduce || recording
            ? {}
            : { scale: [1, 1.035, 1] }
        }
        transition={
          reduce || recording
            ? {}
            : { duration: 4.5, repeat: Infinity, ease: 'easeInOut' }
        }
        className={cn(
          'relative grid place-items-center rounded-full border text-white transition-colors',
          dimension,
          recording
            ? 'border-red-400/50 bg-gradient-to-br from-red-500/90 to-rose-600/80 shadow-[0_0_60px_-10px_rgba(239,68,68,0.8)]'
            : 'border-white/15 bg-gradient-to-br from-primary via-primary-dark to-accent shadow-glow',
          busy && 'cursor-wait opacity-80',
        )}
      >
        <span className={cn('grid place-items-center rounded-full bg-black/15', inner)}>
          {busy ? (
            <Loader2 className="h-8 w-8 animate-spin" />
          ) : recording ? (
            <Square className="h-8 w-8 fill-white" />
          ) : (
            <Mic className="h-9 w-9" />
          )}
        </span>
      </motion.button>
    </div>
  )
}
