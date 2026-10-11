import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import type { Project, StylePreset } from '../api/types'

export type Overrides = Record<string, unknown>
export type DurationOptionKind = 'adjust_delivery' | 'speed_only' | 'edit_script'

export interface Draft {
  script: string
  targetText: string
  targetSeconds: number | null
  durationOption: DurationOptionKind | null
  speed: number
  energy: number
  voice: { engine: string; voice_id: string }
  format: string
  captions: { preset: string; overrides: Overrides; font: string | null }
  background: {
    type: 'solid' | 'transparent' | 'image' | 'video'
    color: string
    path: string | null
    fileName: string | null
    blur: number
    darken: number
  }
  export: { video: 'mp4' | 'webm' | 'mov'; quality: 'fast' | 'balanced' | 'high' }
}

export const DEFAULT_DRAFT: Draft = {
  script: '',
  targetText: '',
  targetSeconds: null,
  durationOption: null,
  speed: 1,
  energy: 0.5,
  voice: { engine: 'edge', voice_id: 'en-US-AvaNeural' },
  format: 'reels',
  captions: { preset: 'bold-pop', overrides: {}, font: null },
  background: { type: 'solid', color: '#101010', path: null, fileName: null, blur: 0, darken: 0 },
  export: { video: 'mp4', quality: 'balanced' },
}

interface DraftStore extends Draft {
  patch: (partial: Partial<Draft>) => void
  setCaptions: (partial: Partial<Draft['captions']>) => void
  setOverride: (path: string, value: unknown) => void
  clearOverrides: () => void
  setBackground: (partial: Partial<Draft['background']>) => void
  setExport: (partial: Partial<Draft['export']>) => void
  load: (project: Project) => void
  reset: () => void
}

/** Immutable set of a dotted path inside a nested object. */
export function setIn(obj: Overrides, path: string, value: unknown): Overrides {
  const [head, ...rest] = path.split('.')
  if (rest.length === 0) return { ...obj, [head]: value }
  const child = (obj[head] as Overrides | undefined) ?? {}
  return { ...obj, [head]: setIn(child, rest.join('.'), value) }
}

export function getIn(obj: unknown, path: string): unknown {
  return path.split('.').reduce<unknown>((o, k) => (o as Record<string, unknown> | undefined)?.[k], obj)
}

export const useDraft = create<DraftStore>()(
  persist(
    (set) => ({
      ...DEFAULT_DRAFT,
      patch: (partial) => set(partial),
      setCaptions: (partial) => set((s) => ({ captions: { ...s.captions, ...partial } })),
      setOverride: (path, value) =>
        set((s) => ({ captions: { ...s.captions, overrides: setIn(s.captions.overrides, path, value) } })),
      clearOverrides: () => set((s) => ({ captions: { ...s.captions, overrides: {}, font: null } })),
      setBackground: (partial) => set((s) => ({ background: { ...s.background, ...partial } })),
      setExport: (partial) => set((s) => ({ export: { ...s.export, ...partial } })),
      load: (p) => {
        const v = p.voice ?? { engine: 'edge', voice_id: 'en-US-AvaNeural', speed: 1, energy: 0.5 }
        set({
          script: p.script,
          targetSeconds: p.duration?.target_seconds ?? null,
          targetText: '',
          durationOption: (p.duration?.option as DurationOptionKind | null) ?? null,
          speed: v.speed ?? 1,
          energy: v.energy ?? 0.5,
          voice: { engine: v.engine, voice_id: v.voice_id },
          format: p.format ?? 'reels',
          captions: {
            preset: p.captions?.preset ?? 'bold-pop',
            overrides: (p.captions?.overrides as Overrides) ?? {},
            font: p.captions?.font ?? null,
          },
          background: {
            type: p.background?.type ?? 'solid',
            color: p.background?.color ?? '#101010',
            path: p.background?.path ?? null,
            fileName: p.background?.path ? (p.background.path.split(/[\\/]/).pop() ?? null) : null,
            blur: p.background?.blur ?? 0,
            darken: p.background?.darken ?? 0,
          },
          export: {
            video: p.export?.video ?? 'mp4',
            quality: p.export?.quality ?? 'balanced',
          },
        })
      },
      reset: () => set({ ...DEFAULT_DRAFT }),
    }),
    {
      name: 'narrareel.draft',
      version: 1,
      // Kept for this tab only, so a reload does not lose work but a new visit starts clean
      // (the start screen offers to continue). Storage can be missing or blocked; the app
      // must still work without it.
      storage: createJSONStorage(() => {
        try {
          window.localStorage.removeItem('narrareel.draft') // older versions kept drafts forever
          window.sessionStorage.setItem('narrareel.probe', '1')
          window.sessionStorage.removeItem('narrareel.probe')
          return window.sessionStorage
        } catch {
          return { getItem: () => null, setItem: () => {}, removeItem: () => {} }
        }
      }),
      partialize: (s) => {
        const { script, targetText, targetSeconds, durationOption, speed, energy, voice, format, captions, background, export: ex } = s
        // an uploaded background lives on the server; keep only what is still valid after restart
        return { script, targetText, targetSeconds, durationOption, speed, energy, voice, format, captions, background, export: ex }
      },
    },
  ),
)

/** The request body the server understands. */
export function toProject(d: Draft): Project {
  const duration: NonNullable<Project['duration']> = {}
  if (d.targetSeconds) {
    duration.target_seconds = d.targetSeconds
    if (d.durationOption) duration.option = d.durationOption
  }
  return {
    script: d.script,
    duration,
    voice: { engine: d.voice.engine, voice_id: d.voice.voice_id, speed: d.speed, energy: d.energy },
    format: d.format,
    captions: {
      preset: d.captions.preset,
      overrides: d.captions.overrides,
      font: d.captions.font,
    },
    background: {
      type: d.background.type,
      color: d.background.color,
      path: d.background.path,
      blur: d.background.blur,
      darken: d.background.darken,
    },
    export: { video: d.export.video, quality: d.export.quality },
  } as Project
}

/** Everything that changes the narration audio. Same key = the voice can be reused. */
export function voiceKey(d: Draft): string {
  return JSON.stringify([d.script, d.voice, d.speed, d.energy, d.targetSeconds, d.durationOption])
}

/** A preset with the user's overrides folded in (for showing current control values). */
export function effectiveStyle(preset: StylePreset | undefined, overrides: Overrides): StylePreset | undefined {
  if (!preset) return undefined
  const merge = (base: unknown, patch: unknown): unknown => {
    if (patch && typeof patch === 'object' && !Array.isArray(patch) && base && typeof base === 'object') {
      const out: Record<string, unknown> = { ...(base as Record<string, unknown>) }
      for (const [k, v] of Object.entries(patch as Record<string, unknown>)) out[k] = merge(out[k], v)
      return out
    }
    return patch
  }
  return merge(preset, overrides) as StylePreset
}
