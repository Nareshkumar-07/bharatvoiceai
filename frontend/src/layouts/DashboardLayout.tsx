import { useEffect, useState } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { Sidebar } from '@/components/layout/Sidebar'
import { Topbar } from '@/components/layout/Topbar'
import { useAuth } from '@/contexts/AuthContext'
import { LoadingState } from '@/components/ui/States'
import { useLocalStorage } from '@/hooks/useLocalStorage'

export function DashboardLayout() {
  const { user, loading } = useAuth()
  const [drawer, setDrawer] = useState(false)
  const location = useLocation()
  const [reducedMotion] = useLocalStorage('bharatvoice.reducedMotion', false)

  useEffect(() => {
    document.documentElement.dataset.reducedMotion = String(reducedMotion)
  }, [reducedMotion])

  useEffect(() => {
    setDrawer(false)
  }, [location.pathname])

  if (loading) return <LoadingState label="Restoring your session…" />
  if (!user) return <Navigate to="/auth?mode=login" replace state={{ from: location.pathname }} />

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 border-r border-white/[0.06] bg-canvas-900/60 backdrop-blur-xl lg:block">
        <Sidebar />
      </aside>

      <AnimatePresence>
        {drawer && (
          <motion.div className="fixed inset-0 z-50 lg:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setDrawer(false)} aria-hidden />
            <motion.aside
              className="relative h-full w-72 border-r border-white/10 bg-canvas-900/95"
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', damping: 26, stiffness: 260 }}
            >
              <button
                className="absolute right-3 top-4 rounded-lg p-1.5 text-ink-muted hover:bg-white/5"
                onClick={() => setDrawer(false)}
                aria-label="Close navigation"
              >
                <X className="h-4 w-4" />
              </button>
              <Sidebar onNavigate={() => setDrawer(false)} />
            </motion.aside>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onOpenSidebar={() => setDrawer(true)} />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto w-full max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
