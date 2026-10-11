import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import { DEFAULT_DRAFT, useDraft } from './state/project'
import { useCatalog } from './state/catalog'

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
})

describe('App', () => {
  it('shows the script step first and blocks Continue until there is a script', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )
    expect(await screen.findByRole('heading', { name: /what should your video say/i })).toBeInTheDocument()
    const next = screen.getByRole('button', { name: /next: choose a voice/i })
    expect(next).toBeDisabled()
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
    expect(screen.getByRole('button', { name: /next: choose a voice/i })).toBeEnabled()
  })

  it('marks the current step in the navigation', async () => {
    render(
      <MemoryRouter initialEntries={['/voice']}>
        <App />
      </MemoryRouter>,
    )
    const link = await screen.findByRole('link', { name: 'Voice' })
    expect(link).toHaveAttribute('aria-current', 'page')
  })
})
