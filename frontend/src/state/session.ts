import { create } from 'zustand'
import type { JobStatus } from '../api/types'

export interface Toast {
  id: number
  kind: 'error' | 'info' | 'success'
  message: string
}

interface Session {
  /** Set once the person picks new, continue or open on the start screen. Not kept across reloads. */
  started: boolean
  /** The last finished (or running) video job and which narration it carries. */
  job: JobStatus | null
  jobVoiceKey: string | null
  progress: { stage: string; fraction: number; message: string } | null
  toasts: Toast[]
  start: () => void
  setJob: (job: JobStatus | null, voiceKey?: string | null) => void
  setProgress: (p: Session['progress']) => void
  toast: (kind: Toast['kind'], message: string) => void
  dismiss: (id: number) => void
}

let nextToast = 1

export const useSession = create<Session>((set, get) => ({
  started: false,
  job: null,
  jobVoiceKey: null,
  progress: null,
  toasts: [],
  start: () => set({ started: true }),
  setJob: (job, voiceKey) =>
    set((s) => ({ job, jobVoiceKey: voiceKey === undefined ? s.jobVoiceKey : voiceKey })),
  setProgress: (progress) => set({ progress }),
  toast: (kind, message) => {
    const id = nextToast++
    set((s) => ({ toasts: [...s.toasts.slice(-3), { id, kind, message }] }))
    if (kind !== 'error') window.setTimeout(() => get().dismiss(id), 5000)
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))
