/** Neural-processing visual shown while the engine is working. */
import { motion, useReducedMotion } from 'framer-motion'

const STAGES = ['Audio in', 'Language ID', 'Recognition', 'Fusion', 'Transcript']

export function ProcessingNeural({ stage = 2 }: { stage?: number }) {
  const reduce = useReducedMotion()
  return (
    <div className="flex flex-col items-center gap-6 py-4">
      <div className="relative h-32 w-64">
        <svg viewBox="0 0 260 130" className="h-full w-full">
          <defs>
            <linearGradient id="pn-grad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#8B5CF6" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#06B6D4" stopOpacity="0.9" />
            </linearGradient>
          </defs>
          {[0, 1, 2].map((layer) =>
            [0, 1, 2, 3].map((node) => {
              const cx = 40 + layer * 90
              const cy = 24 + node * 27
              return (
                <g key={`${layer}-${node}`}>
                  {layer < 2 &&
                    [0, 1, 2, 3].map((next) => (
                      <line
                        key={next}
                        x1={cx}
                        y1={cy}
                        x2={cx + 90}
                        y2={24 + next * 27}
                        stroke="url(#pn-grad)"
                        strokeWidth="0.7"
                        opacity="0.22"
                      />
                    ))}
                  <motion.circle
                    cx={cx}
                    cy={cy}
                    r="3.4"
                    fill="url(#pn-grad)"
                    animate={reduce ? {} : { opacity: [0.35, 1, 0.35] }}
                    transition={{
                      duration: 2.2,
                      repeat: Infinity,
                      delay: (layer + node) * 0.12,
                    }}
                  />
                </g>
              )
            }),
          )}
          {!reduce && (
            <motion.circle
              r="2.6"
              fill="#A78BFA"
              animate={{ cx: [40, 130, 220], cy: [24, 78, 51] }}
              transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
            />
          )}
        </svg>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-2">
        {STAGES.map((label, i) => (
          <span
            key={label}
            className={
              i <= stage
                ? 'chip border-primary/40 bg-primary/10 text-primary-light'
                : 'chip opacity-50'
            }
          >
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}
