import { useId } from 'react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import type { Quality } from '../api/types'

type ButtonVariant = 'primary' | 'secondary' | 'text' | 'dark-on-yellow'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  busy?: boolean
}

export function Button({ variant = 'secondary', busy, className = '', children, disabled, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      className={`btn btn--${variant} ${className}`.trim()}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      {...rest}
    >
      {busy && <span className="spinner" aria-hidden="true" />}
      {children}
    </button>
  )
}

export function Card({
  children,
  className = '',
  yellow,
  as: Tag = 'div',
}: {
  children: ReactNode
  className?: string
  yellow?: boolean
  as?: 'div' | 'section' | 'article'
}) {
  return <Tag className={`card ${yellow ? 'card--yellow' : ''} ${className}`.trim()}>{children}</Tag>
}

export function Badge({
  children,
  tone = 'plain',
}: {
  children: ReactNode
  tone?: 'plain' | 'yellow' | 'good' | 'warn' | 'bad'
}) {
  return <span className={`badge badge--${tone}`}>{children}</span>
}

const QUALITY_LABEL: Record<Quality, string> = {
  natural: 'Sounds natural',
  noticeable: 'Slightly noticeable',
  strong: 'Clearly noticeable',
  not_recommended: 'Sounds unnatural',
}
const QUALITY_TONE: Record<Quality, 'good' | 'warn' | 'bad' | 'plain'> = {
  natural: 'good',
  noticeable: 'plain',
  strong: 'warn',
  not_recommended: 'bad',
}

export function QualityBadge({ quality }: { quality: Quality }) {
  return <Badge tone={QUALITY_TONE[quality]}>{QUALITY_LABEL[quality]}</Badge>
}

export interface TabItem<T extends string> {
  id: T
  label: string
  hint?: string
  disabled?: boolean
}

/** Segmented tab strip (`category-tab` in the design system). */
export function Tabs<T extends string>({
  items,
  value,
  onChange,
  label,
}: {
  items: TabItem<T>[]
  value: T
  onChange: (id: T) => void
  label: string
}) {
  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {items.map((t) => (
        <button
          key={t.id}
          type="button"
          role="tab"
          aria-selected={value === t.id}
          disabled={t.disabled}
          title={t.hint}
          className={`tab ${value === t.id ? 'tab--active' : ''}`}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}

/** One choice out of a few, shown side by side (energy, voice type, highlight style). */
export function Segmented<T extends string>({
  items,
  value,
  onChange,
  label,
}: {
  items: TabItem<T>[]
  value: T
  onChange: (id: T) => void
  label: string
}) {
  return (
    <div className="segmented" role="radiogroup" aria-label={label}>
      {items.map((t) => (
        <button
          key={t.id}
          type="button"
          role="radio"
          aria-checked={value === t.id}
          disabled={t.disabled}
          title={t.hint}
          className="segmented__item"
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}

export function Slider({
  label,
  value,
  min,
  max,
  step,
  onChange,
  format,
  hint,
  marks,
}: {
  label: string
  value: number
  min: number
  max: number
  step: number
  onChange: (v: number) => void
  format?: (v: number) => string
  hint?: string
  marks?: string[]
}) {
  const id = useId()
  return (
    <div className="field">
      <div className="field__head">
        <label htmlFor={id} className="field__label">
          {label}
        </label>
        <output htmlFor={id} className="field__value">
          {format ? format(value) : value}
        </output>
      </div>
      <input
        id={id}
        className="slider"
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      {marks && (
        <div className="slider__marks" aria-hidden="true">
          {marks.map((m) => (
            <span key={m}>{m}</span>
          ))}
        </div>
      )}
      {hint && <p className="field__hint">{hint}</p>}
    </div>
  )
}

export function Switch({
  label,
  checked,
  onChange,
  hint,
}: {
  label: string
  checked: boolean
  onChange: (v: boolean) => void
  hint?: string
}) {
  const id = useId()
  return (
    <div className="switch-row">
      <label htmlFor={id} className="switch-row__label">
        {label}
        {hint && <span className="field__hint">{hint}</span>}
      </label>
      <input
        id={id}
        className="switch"
        type="checkbox"
        role="switch"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
    </div>
  )
}

export function Field({
  label,
  children,
  hint,
  htmlFor,
}: {
  label: string
  children: ReactNode
  hint?: string
  htmlFor?: string
}) {
  return (
    <div className="field">
      <label className="field__label" htmlFor={htmlFor}>
        {label}
      </label>
      {children}
      {hint && <p className="field__hint">{hint}</p>}
    </div>
  )
}

export function ColorField({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (hex: string) => void
}) {
  const id = useId()
  const hex = value.slice(0, 7)
  return (
    <div className="color-field">
      <input
        id={id}
        className="color-field__swatch"
        type="color"
        value={/^#[0-9a-fA-F]{6}$/.test(hex) ? hex : '#000000'}
        onChange={(e) => onChange(e.target.value.toUpperCase() + value.slice(7))}
      />
      <label htmlFor={id} className="color-field__label">
        {label}
      </label>
      <code className="color-field__hex">{hex.toUpperCase()}</code>
    </div>
  )
}

export function Banner({
  tone = 'info',
  title,
  children,
  action,
}: {
  tone?: 'info' | 'warn' | 'error' | 'success'
  title?: string
  children?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className={`banner banner--${tone}`} role={tone === 'error' ? 'alert' : 'status'}>
      <div className="banner__body">
        {title && <strong className="banner__title">{title}</strong>}
        {children && <div className="banner__text">{children}</div>}
      </div>
      {action}
    </div>
  )
}

export function ProgressBar({ fraction, label }: { fraction: number; label: string }) {
  const pct = Math.round(Math.min(1, Math.max(0, fraction)) * 100)
  return (
    <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} aria-label={label}>
      <div className="progress__fill" style={{ width: `${pct}%` }} />
    </div>
  )
}

/** Dark code window (`code-window-card`): shows the command or data behind what you see. */
export function CodeWindow({ title, children }: { title: string; children: string }) {
  return (
    <figure className="code-window">
      <figcaption className="code-window__bar">{title}</figcaption>
      <pre className="code-window__body">
        <code>{children}</code>
      </pre>
    </figure>
  )
}
