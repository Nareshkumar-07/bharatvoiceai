import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/Button'

export default function NotFound() {
  return (
    <div className="grid min-h-[60vh] place-items-center px-6 text-center">
      <div>
        <p className="font-mono text-6xl font-semibold text-white/10">404</p>
        <h1 className="mt-3 text-xl font-semibold text-ink">This page does not exist</h1>
        <p className="mt-2 text-sm text-ink-muted">The link may be outdated, or the route moved.</p>
        <Link to="/app" className="mt-6 inline-block">
          <Button>Back to the workspace</Button>
        </Link>
      </div>
    </div>
  )
}
