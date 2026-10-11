import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { STEPS, screenFor } from '../flow'
import { formatDuration } from '../lib/time'
import { useCatalog } from '../state/catalog'
import { useSession } from '../state/session'
import { useDraft } from '../state/project'
import { useScriptInfo } from '../state/scriptInfo'
import { PhoneFrame } from './PhoneFrame'
import { Button } from './ui'

export function Logo() {
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
  const draft = useDraft()
  const current = screenFor(pathname, draft)?.step ?? -1
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

/** Logo and the steps. Opening a project happens on the start screen; saving, once the video is made. */
export function TopNav() {
  return (
    <header className="nav">
      <div className="nav__inner">
        <NavLink to="/" className="nav__home" aria-label="NarraReel start screen">
          <Logo />
        </NavLink>
        <Stepper />
        <span aria-hidden="true" />
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
    { to: '/length', label: 'Length', value: length, empty: 'Set by your script' },
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

/** The right-hand column where the look of the video is decided: the video as it stands. */
export function ReelRail() {
  return (
    <div className="rail">
      <PhoneFrame />
      <Recipe />
    </div>
  )
}

/** Back on the left, the one way forward on the right. */
export function StepNav() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const draft = useDraft()
  const screen = screenFor(pathname, draft)
  // the last step draws its own bar, because its forward action is making the video
  if (!screen || pathname === '/export') return null
  const { back, next } = screen
  return (
    <div className={screen.rail ? 'step-nav' : 'step-nav step-nav--solo'}>
      <div className="step-nav__inner">
        {back ? (
          <Button variant="secondary" onClick={() => navigate(back)}>
            Back
          </Button>
        ) : (
          <span />
        )}
        <div className="step-nav__next">
          {next?.blocked && <span className="step-nav__error">{next.blocked}</span>}
          {next ? (
            <Button variant="primary" className="btn--lg" disabled={!!next.blocked} onClick={() => navigate(next.to)}>
              {next.label}
            </Button>
          ) : (
            <span className="step-nav__error">Pick one above to continue.</span>
          )}
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
