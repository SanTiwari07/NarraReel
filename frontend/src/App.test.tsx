import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import { screenFor } from './flow'
import { DEFAULT_DRAFT, useDraft } from './state/project'
import { useCatalog } from './state/catalog'
import { useSession } from './state/session'

const analysis = {
  word_count: 5,
  char_count: 20,
  sentence_count: 1,
  paragraph_count: 1,
  language_hint: 'en',
  warnings: [],
  sentences: [{ idx: 0, text: 'One two three four five.', words: 5, seconds: 1.4, paragraph_idx: 0 }],
  estimate: { speech_seconds: 1.4, pause_seconds: 0.65, total_seconds: 2.05, words_per_minute: 146, basis: 'default' },
  cps: 14,
}

function mockApi() {
  const routes: Record<string, unknown> = {
    '/api/health': { version: '0', ffmpeg: true, libass: true, align_available: false, auth_required: false },
    '/api/presets/formats': [
      { id: 'reels', name: 'Reels / TikTok / Shorts', width: 1080, height: 1920, fps: 30, positions: {}, max_text_width: 0.84, safe_zone: {}, default_style: 'bold-pop', note: '' },
    ],
    '/api/presets/styles': [],
    '/api/fonts': [],
    '/api/engines': [],
    '/api/voices': [],
    '/api/analyze': analysis,
    '/api/plan': { cps: 14, plan: { estimate_1x: analysis.estimate, target_seconds: null, options: [], recommended: 0 } },
  }
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input).split('?')[0]
    if (!(path in routes)) return new Response(JSON.stringify({ error: 'nope' }), { status: 404 })
    return new Response(JSON.stringify(routes[path]), { status: 200, headers: { 'Content-Type': 'application/json' } })
  }) as typeof fetch
}

beforeEach(() => {
  mockApi()
  useDraft.setState({ ...DEFAULT_DRAFT })
  useCatalog.setState({ loaded: false, error: null })
  useSession.setState({ started: true })
})

describe('App', () => {
  it('asks new, continue or open before anything else', async () => {
    useSession.setState({ started: false })
    useDraft.setState({ script: 'An old draft from before.' })
    render(
      <MemoryRouter initialEntries={['/voice']}>
        <App />
      </MemoryRouter>,
    )
    expect(await screen.findByRole('button', { name: /start a new video/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /continue where you left off/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /open a saved project/i })).toBeInTheDocument()
    // saving only appears once a video is made
    expect(screen.queryByRole('button', { name: /save project/i })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /start a new video/i }))
    const box = await screen.findByLabelText('Script')
    expect(box).toHaveValue('')
  })

  it('blocks Next until there is a script', async () => {
    render(
      <MemoryRouter initialEntries={['/script']}>
        <App />
      </MemoryRouter>,
    )
    expect(await screen.findByRole('heading', { name: /what should your video say/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /next: set the length/i })).toBeDisabled()
    expect(screen.getByText(/add a script first/i)).toBeInTheDocument()
  })

  it('updates the live counts as the user types', async () => {
    render(
      <MemoryRouter initialEntries={['/script']}>
        <App />
      </MemoryRouter>,
    )
    const box = await screen.findByLabelText('Script')
    fireEvent.change(box, { target: { value: 'One two three four five.' } })
    await waitFor(() => expect(screen.getByText(/in 1 sentence\./)).toBeInTheDocument(), { timeout: 3000 })
    expect(screen.getByRole('button', { name: /next: set the length/i })).toBeEnabled()
  })

  it('asks for the length on its own screen', async () => {
    render(
      <MemoryRouter initialEntries={['/length']}>
        <App />
      </MemoryRouter>,
    )
    expect(await screen.findByRole('heading', { name: /how long should it be/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /natural length/i })).toHaveAttribute('aria-checked', 'true')
  })

  it('asks which kind of voice first, and marks the step', async () => {
    render(
      <MemoryRouter initialEntries={['/voice']}>
        <App />
      </MemoryRouter>,
    )
    expect(await screen.findByRole('heading', { name: /whose voice should read it/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /an ai voice/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /my own voice/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Voice' })).toHaveAttribute('aria-current', 'page')
  })
})

describe('screenFor', () => {
  it('sends Back from the sound screen to the voice list that was used', () => {
    expect(screenFor('/voice/sound', DEFAULT_DRAFT)?.back).toBe('/voice/ai')
    const own = { ...DEFAULT_DRAFT, voice: { engine: 'chatterbox', voice_id: 'abc' } }
    expect(screenFor('/voice/sound', own)?.back).toBe('/voice/mine')
  })
  it('holds My voice until a saved voice is chosen', () => {
    expect(screenFor('/voice/mine', DEFAULT_DRAFT)?.next?.blocked).toBeTruthy()
    const own = { ...DEFAULT_DRAFT, voice: { engine: 'chatterbox', voice_id: 'abc' } }
    expect(screenFor('/voice/mine', own)?.next?.blocked).toBeFalsy()
  })
})
