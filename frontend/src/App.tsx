import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '@/contexts/AuthContext'
import { ToastProvider } from '@/components/ui/Toast'
import { AmbientBackground } from '@/animations/AmbientBackground'
import { MarketingLayout } from '@/layouts/MarketingLayout'
import { DashboardLayout } from '@/layouts/DashboardLayout'
import { useLocalStorage } from '@/hooks/useLocalStorage'
import { LoadingState } from '@/components/ui/States'

const Landing = lazy(() => import('@/pages/Landing'))
const Auth = lazy(() => import('@/pages/Auth'))
const Overview = lazy(() => import('@/pages/Overview'))
const Workspace = lazy(() => import('@/pages/Workspace'))
const History = lazy(() => import('@/pages/History'))
const Vocabulary = lazy(() => import('@/pages/Vocabulary'))
const LanguageIntelligence = lazy(() => import('@/pages/LanguageIntelligence'))
const AIIntelligence = lazy(() => import('@/pages/AIIntelligence'))
const Analytics = lazy(() => import('@/pages/Analytics'))
const Settings = lazy(() => import('@/pages/Settings'))
const NotFound = lazy(() => import('@/pages/NotFound'))

export default function App() {
  const [reducedMotion] = useLocalStorage('bharatvoice.reducedMotion', false)

  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <AmbientBackground reducedMotion={reducedMotion} />
          <Suspense fallback={<LoadingState label="Loading BharatVoice…" />}>
            <Routes>
              <Route element={<MarketingLayout />}>
                <Route path="/" element={<Landing />} />
              </Route>

              <Route path="/auth" element={<Auth />} />

              <Route path="/app" element={<DashboardLayout />}>
                <Route index element={<Overview />} />
                <Route path="workspace" element={<Workspace />} />
                <Route path="history" element={<History />} />
                <Route path="vocabulary" element={<Vocabulary />} />
                <Route path="languages" element={<LanguageIntelligence />} />
                <Route path="intelligence" element={<AIIntelligence />} />
                <Route path="analytics" element={<Analytics />} />
                <Route path="settings" element={<Settings />} />
              </Route>

              <Route path="/login" element={<Navigate to="/auth?mode=login" replace />} />
              <Route path="/signup" element={<Navigate to="/auth?mode=signup" replace />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
