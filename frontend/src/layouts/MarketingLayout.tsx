import { Link, Outlet, useNavigate } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { BrandMark } from '@/components/layout/Sidebar'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/Button'

export function MarketingLayout() {
  const { user } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-white/[0.05] bg-canvas/60 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center gap-6 px-5">
          <Link to="/" aria-label="BharatVoice AI home">
            <BrandMark />
          </Link>
          <nav className="hidden items-center gap-1 md:flex" aria-label="Sections">
            {[
              ['#why', 'Features'],
              ['#languages', 'Languages'],
              ['#technology', 'Technology'],
              ['#research', 'Research'],
              ['#pricing', 'Pricing'],
            ].map(([href, label]) => (
              <a
                key={href}
                href={href}
                className="rounded-lg px-3 py-2 text-sm text-ink-muted transition-colors hover:bg-white/5 hover:text-ink"
              >
                {label}
              </a>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            {user ? (
              <Button size="sm" iconRight={<ArrowRight className="h-3.5 w-3.5" />} onClick={() => navigate('/app')}>
                Open workspace
              </Button>
            ) : (
              <>
                <Button variant="subtle" size="sm" onClick={() => navigate('/auth?mode=login')}>
                  Sign in
                </Button>
                <Button size="sm" iconRight={<ArrowRight className="h-3.5 w-3.5" />} onClick={() => navigate('/auth?mode=signup')}>
                  Get started
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      <main>
        <Outlet />
      </main>

      <footer className="border-t border-white/[0.06] px-5 py-10">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <BrandMark />
            <p className="mt-3 max-w-md text-xs leading-relaxed text-ink-faint">
              India speaks in thousands of voices. BharatVoice understands the way India communicates.
            </p>
          </div>
          <div className="flex flex-wrap gap-x-8 gap-y-2 text-xs text-ink-faint">
            <Link to="/app/workspace" className="hover:text-ink">Voice workspace</Link>
            <a href="/docs" className="hover:text-ink">API docs</a>
            <a href="#research" className="hover:text-ink">Research</a>
            <span>© {new Date().getFullYear()} BharatVoice AI</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
