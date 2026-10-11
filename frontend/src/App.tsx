import { useEffect } from 'react'
import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { ReelRail, StepNav, TopNav, Toasts } from './components/Shell'
import { Banner, Button } from './components/ui'
import { ScriptInfoProvider } from './state/scriptInfo'
import { useCatalog } from './state/catalog'
import { CaptionsStep } from './steps/CaptionsStep'
import { ExportStep } from './steps/ExportStep'
import { ScriptStep } from './steps/ScriptStep'
import { VoiceStep } from './steps/VoiceStep'

function Layout() {
  const { pathname } = useLocation()
  const { loaded, error, load, health } = useCatalog()
  useEffect(() => {
    void load()
  }, [load])
  // on phones the frame only earns its space where the choices change how it looks
  const stepClass = `workspace--${pathname.slice(1) || 'script'}`

  useEffect(() => {
    window.scrollTo({ top: 0 })
  }, [pathname])

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <TopNav />
      <main id="main" className="page">
        {error && (
          <Banner
            tone="error"
            title="Can’t reach NarraReel"
            action={
              <Button variant="secondary" onClick={() => void load()}>
                Try again
              </Button>
            }
          >
            {error} Check that NarraReel is still running on your computer.
          </Banner>
        )}
        {health?.demo && (
          <Banner tone="info" title="You are using the public demo">
            Scripts are limited to about two minutes, and uploads and voice cloning are off. Install NarraReel on your
            computer to remove the limits.
          </Banner>
        )}
        {loaded && (
          <div className={`workspace ${stepClass}`}>
            <div className="workspace__main">
              <Outlet />
            </div>
            <aside className="workspace__rail" aria-label="Your video">
              <ReelRail />
            </aside>
          </div>
        )}
        {!loaded && !error && <p className="loading">Loading…</p>}
      </main>
      {loaded && <StepNav />}
      <Toasts />
    </>
  )
}

export default function App() {
  return (
    <ScriptInfoProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/script" replace />} />
          <Route path="/script" element={<ScriptStep />} />
          {/* length now lives with the script; old links still land somewhere sensible */}
          <Route path="/duration" element={<Navigate to="/script" replace />} />
          <Route path="/voice" element={<VoiceStep />} />
          <Route path="/captions" element={<CaptionsStep />} />
          <Route path="/export" element={<ExportStep />} />
          <Route path="*" element={<Navigate to="/script" replace />} />
        </Route>
      </Routes>
    </ScriptInfoProvider>
  )
}
