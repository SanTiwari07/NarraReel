import { useEffect } from 'react'
import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { ReelRail, StepNav, TopNav, Toasts } from './components/Shell'
import { Banner, Button } from './components/ui'
import { screenFor } from './flow'
import { ScriptInfoProvider } from './state/scriptInfo'
import { useCatalog } from './state/catalog'
import { useDraft } from './state/project'
import { useSession } from './state/session'
import { CaptionsStep } from './steps/CaptionsStep'
import { ExportStep } from './steps/ExportStep'
import { LengthStep } from './steps/LengthStep'
import { MyVoiceStep } from './steps/MyVoiceStep'
import { ScriptStep } from './steps/ScriptStep'
import { StartScreen } from './steps/StartScreen'
import { AiVoiceStep, SoundStep, VoiceSourceStep } from './steps/VoiceStep'

function Layout() {
  const { pathname } = useLocation()
  const { loaded, error, load, health } = useCatalog()
  const started = useSession((s) => s.started)
  const draft = useDraft()
  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    window.scrollTo({ top: 0 })
  }, [pathname])

  // every visit starts by asking: new video, carry on, or open a project
  if (!started) return <Navigate to="/" replace />

  const screen = screenFor(pathname, draft)
  const rail = !!screen?.rail
  // on phones the frame only earns its space where the choices change how it looks
  const stepClass = pathname === '/captions' ? 'workspace--captions' : ''

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <TopNav />
      <main id="main" className={rail ? 'page' : 'page page--solo'}>
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
        {loaded &&
          (rail ? (
            <div className={`workspace ${stepClass}`}>
              <div className="workspace__main">
                <Outlet />
              </div>
              <aside className="workspace__rail" aria-label="Your video">
                <ReelRail />
              </aside>
            </div>
          ) : (
            <div className="solo">
              <Outlet />
            </div>
          ))}
        {!loaded && !error && <p className="loading">Loading…</p>}
      </main>
      {loaded && <StepNav />}
    </>
  )
}

export default function App() {
  return (
    <ScriptInfoProvider>
      <Routes>
        <Route index element={<StartScreen />} />
        <Route element={<Layout />}>
          <Route path="/script" element={<ScriptStep />} />
          <Route path="/length" element={<LengthStep />} />
          <Route path="/duration" element={<Navigate to="/length" replace />} />
          <Route path="/voice" element={<VoiceSourceStep />} />
          <Route path="/voice/ai" element={<AiVoiceStep />} />
          <Route path="/voice/mine" element={<MyVoiceStep />} />
          <Route path="/voice/sound" element={<SoundStep />} />
          <Route path="/captions" element={<CaptionsStep />} />
          <Route path="/export" element={<ExportStep />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toasts />
    </ScriptInfoProvider>
  )
}
