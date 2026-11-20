import { motion, useReducedMotion } from 'framer-motion'
import { Mic } from 'lucide-react'

const LANGUAGES = [
  { native: 'தமிழ்', angle: 0 },
  { native: 'हिन्दी', angle: 45 },
  { native: 'తెలుగు', angle: 90 },
  { native: 'മലയാളം', angle: 135 },
  { native: 'ಕನ್ನಡ', angle: 180 },
  { native: 'বাংলা', angle: 225 },
  { native: 'मराठी', angle: 270 },
  { native: 'ENGLISH', angle: 315 },
]

export function LanguageOrbit() {
  const reduce = useReducedMotion()
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[520px]">
      {/* concentric rings */}
      {[0.42, 0.62, 0.82, 1].map((scale, i) => (
        <motion.div
          key={scale}
          className="absolute left-1/2 top-1/2 rounded-full border border-white/[0.07]"
          style={{
            width: `${scale * 100}%`,
            height: `${scale * 100}%`,
            transform: 'translate(-50%, -50%)',
          }}
          animate={reduce ? {} : { opacity: [0.35, 0.7, 0.35] }}
          transition={{ duration: 6 + i * 1.4, repeat: Infinity, ease: 'easeInOut' }}
        />
      ))}

      {/* rotating sweep */}
      {!reduce && (
        <motion.div
          className="absolute left-1/2 top-1/2 h-[92%] w-[92%] -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{
            background:
              'conic-gradient(from 0deg, rgba(139,92,246,0.0) 0deg, rgba(139,92,246,0.22) 40deg, rgba(6,182,212,0.16) 80deg, transparent 130deg)',
            maskImage: 'radial-gradient(circle, transparent 48%, #000 50%, #000 70%, transparent 72%)',
            WebkitMaskImage: 'radial-gradient(circle, transparent 48%, #000 50%, #000 70%, transparent 72%)',
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: 22, repeat: Infinity, ease: 'linear' }}
        />
      )}

      {/* central microphone */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
        <motion.div
          className="relative grid h-28 w-28 place-items-center rounded-full border border-white/15 bg-gradient-to-br from-primary via-primary-dark to-accent shadow-glow"
          animate={reduce ? {} : { scale: [1, 1.045, 1] }}
          transition={{ duration: 4.5, repeat: Infinity, ease: 'easeInOut' }}
        >
          <span className="grid h-[72px] w-[72px] place-items-center rounded-full bg-black/20">
            <Mic className="h-8 w-8 text-white" />
          </span>
        </motion.div>
        <div className="pointer-events-none absolute inset-0 -z-10 rounded-full bg-primary/30 blur-3xl" />
      </div>

      {/* language labels */}
      {LANGUAGES.map((lang, i) => {
        const rad = (lang.angle * Math.PI) / 180
        const radius = 41
        const x = 50 + radius * Math.cos(rad)
        const y = 50 + radius * Math.sin(rad)
        return (
          <div
            key={lang.native}
            className="fade-up absolute -translate-x-1/2 -translate-y-1/2"
            style={{ left: `${x}%`, top: `${y}%`, animationDelay: `${0.2 + i * 0.08}s` }}
          >
            <motion.div
              className="glass whitespace-nowrap rounded-xl px-3 py-1.5 text-xs font-medium text-ink shadow-lg"
              animate={reduce ? {} : { y: [0, -6, 0] }}
              transition={{ duration: 6 + i * 0.5, repeat: Infinity, ease: 'easeInOut', delay: i * 0.3 }}
            >
              <span className="indic text-[13px]">{lang.native}</span>
            </motion.div>
          </div>
        )
      })}
    </div>
  )
}
