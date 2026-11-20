import { useEffect, useRef, useState, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  delay?: number
  y?: number
  className?: string
}

/**
 * Scroll reveal built on CSS transitions.
 *
 * Content is never left invisible: an IntersectionObserver flips the class, and
 * a timer forces the visible state if the observer never fires (background tab,
 * headless render, blocked observer). Reduced motion skips the transition
 * entirely via CSS.
 */
export function Reveal({ children, delay = 0, className }: Props) {
  const ref = useRef<HTMLDivElement | null>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const node = ref.current
    if (!node) return

    const fallback = window.setTimeout(() => setVisible(true), 900 + delay * 1000)

    if (typeof IntersectionObserver === 'undefined') {
      setVisible(true)
      return () => window.clearTimeout(fallback)
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setVisible(true)
            observer.disconnect()
          }
        }
      },
      { rootMargin: '0px 0px -60px 0px', threshold: 0.05 },
    )
    observer.observe(node)

    return () => {
      window.clearTimeout(fallback)
      observer.disconnect()
    }
  }, [delay])

  return (
    <div
      ref={ref}
      className={`reveal ${visible ? 'is-visible' : ''} ${className ?? ''}`}
      style={{ transitionDelay: `${delay}s` }}
    >
      {children}
    </div>
  )
}
