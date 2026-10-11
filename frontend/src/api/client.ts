import type {
  AnalyzeResponse,
  CloneResult,
  QualityReport,
  VoiceProfile,
  EngineInfo,
  FontInfo,
  FormatInfo,
  Health,
  JobStatus,
  ModelStorage,
  PlanResponse,
  Project,
  StylePreset,
  Voice,
  VoiceSelection,
} from './types'

const TOKEN_KEY = 'narrareel.token'

/** The access token, taken from `?token=` once and kept for the session (only needed off-loopback). */
export function getToken(): string | null {
  try {
    const fromUrl = new URLSearchParams(window.location.search).get('token')
    if (fromUrl) {
      sessionStorage.setItem(TOKEN_KEY, fromUrl)
      const clean = new URL(window.location.href)
      clean.searchParams.delete('token')
      window.history.replaceState({}, '', clean)
    }
    return sessionStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export class ApiError extends Error {
  status: number
  kind: string
  constructor(message: string, status: number, kind: string) {
    super(message)
    this.status = status
    this.kind = kind
  }
}

function headers(extra?: HeadersInit): Headers {
  const h = new Headers(extra)
  const token = getToken()
  if (token) h.set('Authorization', `Bearer ${token}`)
  return h
}

async function fail(res: Response): Promise<never> {
  let message = `The request failed (${res.status}).`
  let kind = 'HTTPError'
  try {
    const body = await res.json()
    if (body?.error) message = String(body.error)
    if (body?.type) kind = String(body.type)
  } catch {
    /* not JSON */
  }
  if (res.status === 401) message = 'This server needs an access token. Open the link that includes ?token=…'
  throw new ApiError(message, res.status, kind)
}

async function send(path: string, init: RequestInit = {}): Promise<Response> {
  let res: Response
  try {
    res = await fetch(path, { ...init, headers: headers(init.headers) })
  } catch {
    throw new ApiError(
      'Could not reach the NarraReel server. Is `narrareel serve` still running?',
      0,
      'NetworkError',
    )
  }
  if (!res.ok) await fail(res)
  return res
}

function json(body: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

export async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  return (await send(path, { signal })).json()
}

export async function postJson<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return (await send(path, { ...json(body), signal })).json()
}

async function postBlob(path: string, body: unknown, signal?: AbortSignal): Promise<Blob> {
  return (await send(path, { ...json(body), signal })).blob()
}

/** URL for media elements (they can't send headers, so the token rides in the query). */
export function mediaUrl(path: string): string {
  const token = getToken()
  if (!token) return path
  return `${path}${path.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`
}

export const api = {
  health: () => getJson<Health>('/api/health'),
  engines: () => getJson<EngineInfo[]>('/api/engines'),
  prepareEngine: (id: string) => postJson<{ task_id: string }>(`/api/engines/${id}/prepare`, {}),
  installEngine: (id: string) => postJson<{ task_id: string }>(`/api/engines/${id}/install`, {}),
  modelStorage: () => getJson<ModelStorage>('/api/storage/models'),
  /** Opens the system folder window on the computer NarraReel runs on. */
  browseModelFolder: () => postJson<{ path: string | null }>('/api/storage/models/browse', {}),
  keepModelFolder: () => postJson<ModelStorage>('/api/storage/models/keep', {}),
  setModelFolder: async (path: string): Promise<{ task_id: string }> =>
    (await send('/api/storage/models', { ...json({ path }), method: 'PUT' })).json(),
  voices: (engine?: string) =>
    getJson<Voice[]>(`/api/voices${engine ? `?engine=${encodeURIComponent(engine)}` : ''}`),
  fonts: () => getJson<FontInfo[]>('/api/fonts'),
  formats: () => getJson<FormatInfo[]>('/api/presets/formats'),
  styles: () => getJson<StylePreset[]>('/api/presets/styles'),
  saveStyle: (body: { name: string; preset: string; overrides: unknown; font: string | null }) =>
    postJson<StylePreset>('/api/presets/styles', body),
  analyze: (text: string, voice?: string, signal?: AbortSignal) =>
    postJson<AnalyzeResponse>('/api/analyze', { text, voice }, signal),
  plan: (
    body: { text: string; voice?: string; target_seconds?: number | null },
    signal?: AbortSignal,
  ) => postJson<PlanResponse>('/api/plan', body, signal),
  parseDuration: (text: string, signal?: AbortSignal) =>
    postJson<{ seconds: number; formatted: string }>('/api/duration/parse', { text }, signal),
  voicePreview: (text: string, voice: VoiceSelection) =>
    postBlob('/api/preview/voice', { text, voice }),
  framePreview: (project: Project, signal?: AbortSignal) =>
    postBlob('/api/preview/frame', { project }, signal),
  createJob: (project: Project) => postJson<{ job_id: string }>('/api/jobs', { project }),
  rerender: (jobId: string, project: Project) =>
    postJson<{ job_id: string }>(`/api/jobs/${jobId}/rerender`, { project }),
  cancelJob: (jobId: string) => postJson<{ cancelled: boolean }>(`/api/jobs/${jobId}/cancel`, {}),
  job: (jobId: string) => getJson<JobStatus>(`/api/jobs/${jobId}`),
  validateProject: (project: unknown) =>
    postJson<Project>('/api/project/validate', { project }),
  guidedText: () => getJson<Record<string, string>>('/api/voices/guided-text'),
  customVoices: () => getJson<VoiceProfile[]>('/api/voices/custom'),
  checkRecording: async (blob: Blob): Promise<QualityReport> => {
    const form = new FormData()
    form.append('file', blob, 'recording.webm')
    return (await send('/api/voices/clone/check', { method: 'POST', body: form })).json()
  },
  cloneVoice: async (blob: Blob, name: string, consent: boolean, language: string): Promise<CloneResult> => {
    const form = new FormData()
    form.append('file', blob, 'recording.webm')
    form.append('name', name)
    form.append('consent', String(consent))
    form.append('language', language)
    return (await send('/api/voices/clone', { method: 'POST', body: form })).json()
  },
  deleteVoice: async (id: string) => {
    await send(`/api/voices/custom/${encodeURIComponent(id)}`, { method: 'DELETE' })
  },
  importVoice: async (file: File): Promise<VoiceProfile> => {
    const form = new FormData()
    form.append('file', file)
    return (await send('/api/voices/custom/import', { method: 'POST', body: form })).json()
  },
  uploadFont: async (file: File): Promise<FontInfo> => {
    const form = new FormData()
    form.append('file', file)
    return (await send('/api/fonts', { method: 'POST', body: form })).json()
  },
  uploadBackground: async (
    file: File,
  ): Promise<{ path: string; type: 'image' | 'video'; name: string; size: number }> => {
    const form = new FormData()
    form.append('file', file)
    return (await send('/api/backgrounds', { method: 'POST', body: form })).json()
  },
}

export const fontPreviewUrl = (id: string, text?: string) =>
  mediaUrl(`/api/fonts/${id}/preview.png${text ? `?text=${encodeURIComponent(text)}` : ''}`)

export const voiceSampleUrl = (engine: string, id: string) =>
  mediaUrl(`/api/voices/${encodeURIComponent(engine)}/${encodeURIComponent(id)}/sample`)

export const customVoiceUrl = (id: string, what: 'reference.mp3' | 'export') =>
  mediaUrl(`/api/voices/custom/${encodeURIComponent(id)}/${what}`)

export const jobFileUrl = (jobId: string, name: string, download = false) =>
  mediaUrl(`/api/jobs/${jobId}/files/${name}${download ? '?download=true' : ''}`)

/** Subscribe to a job's progress. Returns a function that closes the stream. */
export function watchJob(
  jobId: string,
  onEvent: (e: { stage: string; fraction: number; message: string }) => void,
  onEnd: (status: JobStatus) => void,
  onLost: () => void,
  kind: 'jobs' | 'tasks' = 'jobs',
): () => void {
  const source = new EventSource(mediaUrl(`/api/${kind}/${jobId}/events`))
  let ended = false
  source.addEventListener('progress', (ev) => onEvent(JSON.parse((ev as MessageEvent).data)))
  source.addEventListener('end', (ev) => {
    ended = true
    source.close()
    onEnd(JSON.parse((ev as MessageEvent).data))
  })
  source.onerror = () => {
    if (!ended) {
      source.close()
      onLost()
    }
  }
  return () => {
    ended = true
    source.close()
  }
}
