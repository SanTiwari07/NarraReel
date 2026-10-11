import type { Draft } from './state/project'

/** The five things a person decides, in the order they decide them. */
export const STEPS = [
  { path: '/script', label: 'Script' },
  { path: '/length', label: 'Length' },
  { path: '/voice', label: 'Voice' },
  { path: '/captions', label: 'Captions' },
  { path: '/export', label: 'Make video' },
] as const

export interface Screen {
  /** Index into STEPS: which step the stepper shows as current. */
  step: number
  back: string | null
  /** No `next` means the screen moves on by itself (a choice) or draws its own bar. */
  next?: { to: string; label: string; blocked?: string | null }
  /** Screens where the caption preview matters keep it beside the controls. */
  rail?: boolean
}

const ownVoice = (d: Draft) => d.voice.engine === 'chatterbox'

/** One question per screen. Back and Next depend on what was answered before. */
export function screenFor(pathname: string, d: Draft): Screen | null {
  switch (pathname) {
    case '/script':
      return {
        step: 0,
        back: '/',
        next: { to: '/length', label: 'Next: set the length', blocked: d.script.trim() ? null : 'Add a script first.' },
      }
    case '/length':
      return { step: 1, back: '/script', next: { to: '/voice', label: 'Next: choose a voice' } }
    case '/voice':
      return { step: 2, back: '/length' }
    case '/voice/ai':
      return {
        step: 2,
        back: '/voice',
        next: { to: '/voice/sound', label: 'Next: how it sounds', blocked: ownVoice(d) ? 'Pick a voice first.' : null },
      }
    case '/voice/mine':
      return {
        step: 2,
        back: '/voice',
        next: { to: '/voice/sound', label: 'Next: how it sounds', blocked: ownVoice(d) ? null : 'Pick or save your voice first.' },
      }
    case '/voice/sound':
      return {
        step: 2,
        back: ownVoice(d) ? '/voice/mine' : '/voice/ai',
        next: { to: '/captions', label: 'Next: style the captions' },
      }
    case '/captions':
      return { step: 3, back: '/voice/sound', next: { to: '/export', label: 'Next: make the video' }, rail: true }
    case '/export':
      return { step: 4, back: '/captions', rail: true }
    default:
      return null
  }
}
