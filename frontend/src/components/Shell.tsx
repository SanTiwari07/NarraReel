import { useRef } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { formatDuration } from '../lib/time'
import { useCatalog } from '../state/catalog'
import { useSession } from '../state/session'
import { toProject, useDraft } from '../state/project'
import { useScriptInfo } from '../state/scriptInfo'
import { PhoneFrame } from './PhoneFrame'
import { Button } from './ui'

/** The four things a person decides, in the order they decide them. */
export const STEPS = [
  { path: '/script', label: 'Script', next: 'Next: choose a voice' },
  { path: '/voice', label: 'Voice', next: 'Next: style the captions' },
  { path: '/captions', label: 'Captions', next: 'Next: make the video' },
  { path: '/export', label: 'Make video', next: '' },
] as const

function Logo() {
  return (
    <span className="brand">
      <svg className="brand__mark" viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="7" fill="var(--color-primary)" />
        <rect x="6" y="9" width="12" height="4" rx="2" fill="var(--color-on-primary)" />
        <rect x="6" y="15" width="20" height="4" rx="2" fill="var(--color-on-primary)" />
        <rect x="6" y="21" width="8" height="4" rx="2" fill="var(--color-on-primary)" />
      </svg>
      <span className="brand__name">NarraReel</span>
    </span>
  )
}

function Check() {
  return (
    <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
      <path d="M3 8.5l3 3 7-7" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function Stepper() {
  const { pathname } = useLocation()
  const current = STEPS.findIndex((s) => s.path === pathname)
  return (
    <nav className="stepper" aria-label="Steps">
      <ol className="stepper__list">
        {STEPS.map((s, i) => {
          const state = i < current ? 'done' : i === current ? 'now' : 'todo'
          return (
            <li key={s.path} className={`stepper__item stepper__item--${state}`}>
              <NavLink to={s.path} className="stepper__link">
                <span className="stepper__dot" aria-hidden="true">
                  {state === 'done' ? <Check /> : i + 1}
                </span>
                <span className="stepper__label">{s.label}</span>
                {state === 'done' && <span className="sr-only"> (done)</span>}
              </NavLink>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}

export function TopNav() {
  const fileRef = useRef<HTMLInputElement>(null)
  const toast = useSession((s) => s.toast)
  const load = useDraft((s) => s.load)

  const openProject = async (file: File) => {
    try {
      const raw = JSON.parse(await file.text())
      const project = await api.validateProject(raw)
      load(project)
      toast('success', `Opened ${file.name}`)
    } catch (e) {
      toast('error', e instanceof Error ? e.message : 'That file is not a NarraReel project.')
    }
  }

  const saveProject = () => {
    const project = toProject(useDraft.getState())
    const blob = new Blob([JSON.stringify(project, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'project.narrareel.json'
    a.click()
    window.setTimeout(() => URL.revokeObjectURL(a.href), 1000)
    toast('success', 'Project saved. Open it any time to keep editing.')
  }

  return (
    <header className="nav">
      <div className="nav__inner">
        <NavLink to="/script" className="nav__home" aria-label="NarraReel home">
          <Logo />
        </NavLink>
        <Stepper />
        <div className="nav__actions">
          <input
            ref={fileRef}
            type="file"
            accept=".json,application/json"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) void openProject(f)
              e.target.value = ''
            }}
          />
          <Button variant="text" onClick={() => fileRef.current?.click()} title="Open a saved project file">
            Open project
          </Button>
          <Button variant="text" onClick={saveProject} title="Save everything to a file you can open later">
            Save project
          </Button>
        </div>
      </div>
    </header>
  )
}

/** What the video is made of so far. Each line jumps back to the step that sets it. */
function Recipe() {
  const info = useScriptInfo()
  const { voice, targetSeconds, format, captions, script } = useDraft()
  const voices = useCatalog((s) => s.voices)
  const formats = useCatalog((s) => s.formats)
  const styles = useCatalog((s) => s.styles)
  const voiceName =
    voices.find((v) => v.engine === voice.engine && v.id === voice.voice_id)?.name ??
    voice.voice_id.split('-').at(-1)?.replace('Neural', '')
  const fmt = formats.find((f) => f.id === format)
  const style = styles.find((s) => s.id === captions.preset)
  const a = info.analysis.data
  const hasScript = !!script.trim() && !!a && a.word_count > 0
  const length = targetSeconds ? formatDuration(targetSeconds) : hasScript ? `About ${formatDuration(a.estimate.total_seconds)}` : null

  const rows = [
    { to: '/script', label: 'Script', value: hasScript ? `${a.word_count} words` : null, empty: 'Not written yet' },
    { to: '/script', label: 'Length', value: length, empty: 'Set by your script' },
    { to: '/voice', label: 'Voice', value: voiceName ?? null, empty: 'Not chosen' },
    { to: '/captions', label: 'Captions', value: style?.name ?? null, empty: 'Not chosen' },
    { to: '/captions', label: 'Format', value: fmt ? fmt.name.split(' (')[0].split(' / ')[0] : null, empty: 'Not chosen' },
  ]
  return (
    <ul className="recipe" aria-label="Your video so far">
      {rows.map((r) => (
        <li key={r.label}>
          <NavLink to={r.to} className="recipe__row">
            <span className="recipe__label">{r.label}</span>
            <span className={r.value ? 'recipe__value' : 'recipe__value recipe__value--empty'}>{r.value ?? r.empty}</span>
          </NavLink>
        </li>
      ))}
    </ul>
  )
}

/** The right-hand column on every step: the video as it stands, and what it is made of. */
export function ReelRail() {
  return (
    <div className="rail">
      <PhoneFrame />
      <Recipe />
    </div>
  )
}

export function StepNav() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const script = useDraft((s) => s.script)
  const i = STEPS.findIndex((s) => s.path === pathname)
  if (i < 0) return null
  const prev = STEPS[i - 1]
  const next = STEPS[i + 1]
  const blocked = i === 0 && !script.trim()
  // the last step draws its own bar, because its forward action is making the video
  if (!next) return null
  return (
    <div className="step-nav">
      <div className="step-nav__inner">
        {prev ? (
          <Button variant="text" onClick={() => navigate(prev.path)}>
            Back
          </Button>
        ) : (
          <span />
        )}
        <div className="step-nav__next">
          {blocked && <span className="step-nav__error">Add a script first.</span>}
          <Button variant="primary" className="btn--lg" disabled={blocked} onClick={() => navigate(next.path)}>
            {STEPS[i].next}
          </Button>
        </div>
      </div>
    </div>
  )
}

export function Toasts() {
  const { toasts, dismiss } = useSession()
  return (
    <div className="toasts" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast--${t.kind}`} role={t.kind === 'error' ? 'alert' : 'status'}>
          <span>{t.message}</span>
          <button type="button" className="toast__close" onClick={() => dismiss(t.id)} aria-label="Dismiss message">
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
