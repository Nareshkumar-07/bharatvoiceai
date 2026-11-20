/**
 * Ambient AI atmosphere: gradient wash + floating particles + constellation lines.
 * Canvas-based, capped at ~60fps, pauses when the tab is hidden, and switches off
 * entirely when reduced motion is requested.
 */
import { useEffect, useRef } from 'react'

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  r: number
  hue: number
}

export function AmbientBackground({ reducedMotion = false }: { reducedMotion?: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    if (reducedMotion) return
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let width = 0
    let height = 0
    let dpr = Math.min(window.devicePixelRatio || 1, 2)
    let particles: Particle[] = []
    let raf = 0
    let running = true

    const resize = () => {
      width = window.innerWidth
      height = window.innerHeight
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = width * dpr
      canvas.height = height * dpr
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

      const density = Math.min(78, Math.floor((width * height) / 26000))
      particles = Array.from({ length: density }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.18,
        vy: (Math.random() - 0.5) * 0.18,
        r: Math.random() * 1.7 + 0.5,
        hue: Math.random() > 0.5 ? 262 : 189,
      }))
    }

    const draw = () => {
      if (!running) return
      ctx.clearRect(0, 0, width, height)

      // constellation links (network feel), capped to keep it cheap
      const maxDist = 132
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i]
        for (let j = i + 1; j < particles.length; j++) {
          const q = particles[j]
          const dx = p.x - q.x
          const dy = p.y - q.y
          const dist = Math.hypot(dx, dy)
          if (dist < maxDist) {
            const alpha = (1 - dist / maxDist) * 0.14
            ctx.strokeStyle = `hsla(${(p.hue + q.hue) / 2}, 90%, 72%, ${alpha})`
            ctx.lineWidth = 0.6
            ctx.beginPath()
            ctx.moveTo(p.x, p.y)
            ctx.lineTo(q.x, q.y)
            ctx.stroke()
          }
        }
      }

      for (const p of particles) {
        p.x += p.vx
        p.y += p.vy
        if (p.x < -20) p.x = width + 20
        if (p.x > width + 20) p.x = -20
        if (p.y < -20) p.y = height + 20
        if (p.y > height + 20) p.y = -20

        const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 6)
        grad.addColorStop(0, `hsla(${p.hue}, 95%, 78%, 0.55)`)
        grad.addColorStop(1, `hsla(${p.hue}, 95%, 60%, 0)`)
        ctx.fillStyle = grad
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r * 6, 0, Math.PI * 2)
        ctx.fill()

        ctx.fillStyle = `hsla(${p.hue}, 100%, 92%, 0.8)`
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r * 0.6, 0, Math.PI * 2)
        ctx.fill()
      }

      raf = requestAnimationFrame(draw)
    }

    const onVisibility = () => {
      if (document.hidden) {
        running = false
        cancelAnimationFrame(raf)
      } else if (!running) {
        running = true
        raf = requestAnimationFrame(draw)
      }
    }

    resize()
    raf = requestAnimationFrame(draw)
    window.addEventListener('resize', resize)
    document.addEventListener('visibilitychange', onVisibility)

    return () => {
      running = false
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [reducedMotion])

  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      {/* base gradient */}
      <div className="absolute inset-0 bg-canvas" />
      {/* slow-moving colour wash */}
      {!reducedMotion && (
        <>
          <div
            className="absolute -left-40 top-[-10%] h-[46rem] w-[46rem] rounded-full opacity-60 blur-[130px]"
            style={{
              background: 'radial-gradient(circle, rgba(139,92,246,0.30), transparent 65%)',
              animation: 'float 18s ease-in-out infinite',
            }}
          />
          <div
            className="absolute right-[-15%] top-[18%] h-[38rem] w-[38rem] rounded-full opacity-50 blur-[140px]"
            style={{
              background: 'radial-gradient(circle, rgba(6,182,212,0.26), transparent 65%)',
              animation: 'float 24s ease-in-out infinite reverse',
            }}
          />
          <div
            className="absolute bottom-[-20%] left-[25%] h-[40rem] w-[40rem] rounded-full opacity-40 blur-[150px]"
            style={{
              background: 'radial-gradient(circle, rgba(167,139,250,0.24), transparent 70%)',
              animation: 'float 30s ease-in-out infinite',
            }}
          />
        </>
      )}
      {/* grid */}
      <div
        className="absolute inset-0 opacity-[0.35] mask-fade-b"
        style={{
          backgroundImage:
            'linear-gradient(to right, rgba(148,163,184,0.07) 1px, transparent 1px), linear-gradient(to bottom, rgba(148,163,184,0.07) 1px, transparent 1px)',
          backgroundSize: '56px 56px',
          maskImage: 'radial-gradient(ellipse at 50% 0%, #000 40%, transparent 78%)',
          WebkitMaskImage: 'radial-gradient(ellipse at 50% 0%, #000 40%, transparent 78%)',
        }}
      />
      {!reducedMotion && <canvas ref={canvasRef} className="absolute inset-0" />}
      {/* vignette */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_35%,rgba(8,11,20,0.85)_100%)]" />
    </div>
  )
}
