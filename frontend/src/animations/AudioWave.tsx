/**
 * Waveform renderer. The values come from the AnalyserNode in useRecorder, i.e.
 * real microphone amplitude - not a decorative sine wave.
 */
import { useEffect, useRef } from 'react'

interface Props {
  values: number[]
  active: boolean
  height?: number
  colorFrom?: string
  colorTo?: string
}

export function AudioWave({
  values,
  active,
  height = 96,
  colorFrom = '#8B5CF6',
  colorTo = '#06B6D4',
}: Props) {
  const ref = useRef<HTMLCanvasElement | null>(null)
  const valuesRef = useRef(values)
  valuesRef.current = values

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    let raf = 0

    const render = () => {
      const w = canvas.clientWidth
      const h = height
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, w, h)

      const vals = valuesRef.current
      const barWidth = Math.max(2, w / vals.length - 2)
      const gap = 2
      const mid = h / 2
      const grad = ctx.createLinearGradient(0, 0, w, 0)
      grad.addColorStop(0, colorFrom)
      grad.addColorStop(1, colorTo)

      vals.forEach((v, i) => {
        const amp = Math.max(0.035, Math.min(1, v)) * (h / 2 - 4)
        const x = i * (barWidth + gap)
        const alpha = active ? 0.9 : 0.35
        ctx.fillStyle = grad
        ctx.globalAlpha = alpha
        const radius = Math.min(barWidth / 2, 3)
        ctx.beginPath()
        ctx.roundRect(x, mid - amp, barWidth, amp * 2, radius)
        ctx.fill()
      })
      ctx.globalAlpha = 1

      // centre line
      ctx.strokeStyle = 'rgba(148,163,184,0.18)'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(0, mid)
      ctx.lineTo(w, mid)
      ctx.stroke()

      raf = requestAnimationFrame(render)
    }

    raf = requestAnimationFrame(render)
    return () => cancelAnimationFrame(raf)
  }, [active, colorFrom, colorTo, height])

  return <canvas ref={ref} style={{ height }} className="w-full" aria-hidden />
}
