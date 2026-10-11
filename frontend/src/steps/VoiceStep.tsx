import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, voiceSampleUrl, watchJob } from '../api/client'
import type { Quality, Voice } from '../api/types'
import { Button, CodeWindow, ProgressBar, QualityBadge, Segmented, Slider } from '../components/ui'
import { formatDuration, speedQuality } from '../lib/time'
import { useCatalog } from '../state/catalog'
import { useDraft } from '../state/project'
import { useScriptInfo } from '../state/scriptInfo'
import { useSession } from '../state/session'

type Gender = 'all' | 'female' | 'male'

const LANGUAGE_NAMES: Record<string, string> = {
  en: 'English',
  hi: 'Hindi',
  es: 'Spanish',
  fr: 'French',
  de: 'German',
  it: 'Italian',
  pt: 'Portuguese',
  ja: 'Japanese',
  zh: 'Chinese',
  ar: 'Arabic',
  ru: 'Russian',
  ko: 'Korean',
  bn: 'Bengali',
  ta: 'Tamil',
  te: 'Telugu',
  mr: 'Marathi',
  ur: 'Urdu',
  gu: 'Gujarati',
}

const ENERGY = [
  { id: 'calm', label: 'Calm', value: 0.2 },
  { id: 'normal', label: 'Normal', value: 0.5 },
  { id: 'hype', label: 'Hype', value: 0.85 },
] as const

const energyId = (v: number) => (v < 0.35 ? 'calm' : v > 0.65 ? 'hype' : 'normal')

const PAGE = 24

const shortName = (name: string) => name.replace(/Multilingual$/, '')

/** "US, female" — some names already read "Heart (US, female)", so nothing is said twice. */
function voiceMeta(voice: Voice, showLanguage: boolean): string {
  const named = voice.accent != null && voice.name.includes(`(${voice.accent}`)
  const lang = LANGUAGE_NAMES[voice.language.split('-')[0]] ?? voice.language
  return [showLanguage ? lang : null, named ? null : voice.accent, named || voice.gender === 'unknown' ? null : voice.gender]
    .filter(Boolean)
    .join(', ')
}

export function PlayIcon({ playing }: { playing: boolean }) {
  return playing ? (
    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
      <rect x="3.5" y="3.5" width="9" height="9" rx="1.5" fill="currentColor" />
    </svg>
  ) : (
    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
      <path d="M5 3.2v9.6a.6.6 0 0 0 .9.5l7.6-4.8a.6.6 0 0 0 0-1L5.9 2.7a.6.6 0 0 0-.9.5z" fill="currentColor" />
    </svg>
  )
}

function MicIcon() {
  return (
    <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true">
      <rect x="9" y="3" width="6" height="11" rx="3" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function WaveIcon() {
  return (
    <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true">
      <path d="M3 12h1M7 8v8M11 4v16M15 8v8M19 11v2" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function VoiceTile({
  voice,
  selected,
  playing,
  showLanguage,
  onUse,
  onPlay,
}: {
  voice: Voice
  selected: boolean
  playing: boolean
  showLanguage: boolean
  onUse: () => void
  onPlay: () => void
}) {
  return (
    <li className={`vtile ${selected ? 'vtile--on' : ''}`}>
      <button
        type="button"
        className={`vtile__play ${playing ? 'vtile__play--on' : ''}`}
        onClick={onPlay}
        aria-label={`${playing ? 'Stop' : 'Play'} a sample of ${voice.name}`}
      >
        <PlayIcon playing={playing} />
      </button>
      <button type="button" role="radio" aria-checked={selected} className="vtile__pick" onClick={onUse}>
        <span className="vtile__name">{shortName(voice.name)}</span>
        <span className="vtile__meta">
          {voiceMeta(voice, showLanguage)}
          {voice.offline && <span className="vtile__tag">Works offline</span>}
          {/Multilingual$/.test(voice.name) && <span className="vtile__tag">Speaks many languages</span>}
        </span>
      </button>
      {selected && (
        <span className="vtile__check" aria-hidden="true">
          <svg viewBox="0 0 16 16" width="12" height="12">
            <path d="M3 8.5l3 3 7-7" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      )}
    </li>
  )
}

/** Offline voices: a quiet, optional extra. Most people never need it. */
function OfflineVoices() {
  const engines = useCatalog((s) => s.engines)
  const refreshEngines = useCatalog((s) => s.refreshEngines)
  const refreshVoices = useCatalog((s) => s.refreshVoices)
  const toast = useSession((s) => s.toast)
  const [progress, setProgress] = useState<{ fraction: number; message: string } | null>(null)
  const kokoro = engines.find((e) => e.id === 'kokoro')
  const stop = useRef<(() => void) | null>(null)
  useEffect(() => () => stop.current?.(), [])

  if (!kokoro || (kokoro.status.available && !kokoro.status.needs_download)) return null

  const download = async () => {
    try {
      const { task_id } = await api.prepareEngine('kokoro')
      setProgress({ fraction: 0, message: 'Starting download' })
      stop.current = watchJob(
        task_id,
        (e) => setProgress({ fraction: e.fraction, message: e.message }),
        async (status) => {
          setProgress(null)
          if (status.status === 'done') {
            toast('success', 'Offline voices are ready.')
            await Promise.all([refreshEngines(), refreshVoices()])
          } else toast('error', status.error ?? 'The download did not finish.')
        },
        () => {
          setProgress(null)
          toast('error', 'Lost connection while downloading. Try again.')
        },
        'tasks',
      )
    } catch (e) {
      toast('error', e instanceof Error ? e.message : 'Could not start the download.')
    }
  }

  return (
    <details className="disclosure" open={!!progress}>
      <summary className="disclosure__summary">
        <span>Want voices that work without internet?</span>
      </summary>
      <div className="disclosure__body stack">
        {kokoro.status.available ? (
          <>
            <p>
              Download them once (about {kokoro.status.download_size_mb} MB) and they run on your computer with no
              internet needed.
            </p>
            {progress ? (
              <>
                <ProgressBar fraction={progress.fraction} label="Download progress" />
                <p className="field__hint">{progress.message}</p>
              </>
            ) : (
              <div>
                <Button variant="secondary" onClick={download}>
                  Download offline voices
                </Button>
              </div>
            )}
          </>
        ) : (
          <>
            <p>Offline voices need one extra install. Run this in a terminal, then restart NarraReel.</p>
            <CodeWindow title="Terminal">{'pip install "narrareel[offline]"'}</CodeWindow>
          </>
        )}
      </div>
    </details>
  )
}

/** First question of the voice step: a ready-made voice, or your own? Picking one moves on. */
export function VoiceSourceStep() {
  const navigate = useNavigate()
  const voice = useDraft((s) => s.voice)
  const voices = useCatalog((s) => s.voices)
  const health = useCatalog((s) => s.health)
  const own = voice.engine === 'chatterbox'
  const current = voices.find((v) => v.engine === voice.engine && v.id === voice.voice_id)

  return (
    <div className="step">
      <header className="step-head">
        <h1 className="display">Whose voice should read it?</h1>
        <p className="lede">Pick one. You can come back and change it at any time.</p>
      </header>

      <div className="source-grid">
        <button type="button" className={`source-card ${own ? '' : 'source-card--on'}`} onClick={() => navigate('/voice/ai')}>
          <span className="source-card__icon">
            <WaveIcon />
          </span>
          <span className="source-card__title">An AI voice</span>
          <span className="source-card__text">Hundreds of free voices in many languages, ready right now.</span>
          {!own && current && <span className="source-card__now">Chosen: {shortName(current.name)}</span>}
        </button>
        <button
          type="button"
          className={`source-card ${own ? 'source-card--on' : ''}`}
          disabled={!!health?.demo}
          onClick={() => navigate('/voice/mine')}
        >
          <span className="source-card__icon">
            <MicIcon />
          </span>
          <span className="source-card__title">My own voice</span>
          <span className="source-card__text">
            {health?.demo
              ? 'Not available in the public demo. Install NarraReel to use it.'
              : 'Read one short paragraph aloud, once. Every video then speaks like you.'}
          </span>
          {own && current && <span className="source-card__now">Chosen: {current.name}</span>}
        </button>
      </div>
    </div>
  )
}

/** The ready-made voices: press play to hear one, click it to use it. */
export function AiVoiceStep() {
  const { voice, patch } = useDraft()
  const voices = useCatalog((s) => s.voices)
  const { analysis } = useScriptInfo()
  const toast = useSession((s) => s.toast)
  const [lang, setLang] = useState(analysis.data?.language_hint ?? 'en')
  const [gender, setGender] = useState<Gender>('all')
  const [limit, setLimit] = useState(PAGE)
  const [playing, setPlaying] = useState<string | null>(null)
  const audio = useRef<HTMLAudioElement | null>(null)

  useEffect(() => () => audio.current?.pause(), [])
  useEffect(() => {
    setLimit(PAGE)
  }, [lang, gender])

  const languages = useMemo(() => {
    const seen = new Set(voices.map((v) => v.language.split('-')[0]))
    return [...seen].sort((a, b) => (a === 'en' ? -1 : b === 'en' ? 1 : (LANGUAGE_NAMES[a] ?? a).localeCompare(LANGUAGE_NAMES[b] ?? b)))
  }, [voices])

  const filtered = useMemo(
    () =>
      voices.filter(
        (v) =>
          !v.custom &&
          (lang === 'all' || v.language.startsWith(lang)) &&
          (gender === 'all' || v.gender === gender),
      ),
    [voices, lang, gender],
  )

  const stopAudio = () => {
    audio.current?.pause()
    audio.current = null
    setPlaying(null)
  }

  const play = (v: Voice) => {
    if (playing === v.ref) return stopAudio()
    stopAudio()
    const el = new Audio(voiceSampleUrl(v.engine, v.id))
    audio.current = el
    setPlaying(v.ref)
    el.onended = () => setPlaying(null)
    el.onerror = () => {
      setPlaying(null)
      toast('error', `Could not play ${v.name}. Check your internet connection or pick another voice.`)
    }
    void el.play().catch(() => setPlaying(null))
  }

  const shown = filtered.slice(0, limit)

  return (
    <div className="step">
      <header className="step-head">
        <h1 className="display">Pick an AI voice</h1>
        <p className="lede">Press the yellow button to hear a voice. Click the one you like to use it.</p>
      </header>

      <div className="filter-bar">
        <div className="field filter-bar__lang">
          <label className="field__label" htmlFor="lang-filter">
            Language
          </label>
          <select id="lang-filter" className="select" value={lang} onChange={(e) => setLang(e.target.value)}>
            <option value="all">All languages</option>
            {languages.map((l) => (
              <option key={l} value={l}>
                {LANGUAGE_NAMES[l] ?? l}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <span className="field__label">Sounds</span>
          <Segmented
            label="Voice type"
            value={gender}
            onChange={setGender}
            items={[
              { id: 'all', label: 'Any' },
              { id: 'female', label: 'Female' },
              { id: 'male', label: 'Male' },
            ]}
          />
        </div>
      </div>

      {voices.length === 0 ? (
        <p className="empty">Loading voices…</p>
      ) : filtered.length === 0 ? (
        <p className="empty">No voices match. Try another language, or choose Any.</p>
      ) : (
        <ul className="vtile-grid" role="radiogroup" aria-label="Voices">
          {shown.map((v) => (
            <VoiceTile
              key={v.ref}
              voice={v}
              showLanguage={lang === 'all'}
              selected={voice.engine === v.engine && voice.voice_id === v.id}
              playing={playing === v.ref}
              onUse={() => patch({ voice: { engine: v.engine, voice_id: v.id } })}
              onPlay={() => play(v)}
            />
          ))}
        </ul>
      )}
      {filtered.length > limit && (
        <div className="center">
          <Button variant="secondary" onClick={() => setLimit((l) => l + PAGE)}>
            Show more voices ({filtered.length - limit} left)
          </Button>
        </div>
      )}
      <OfflineVoices />
    </div>
  )
}

/** Last question of the voice step: how lively and how fast, then hear it. */
export function SoundStep() {
  const { voice, speed, energy, script, targetSeconds, patch } = useDraft()
  const voices = useCatalog((s) => s.voices)
  const health = useCatalog((s) => s.health)
  const toast = useSession((s) => s.toast)
  const [previewing, setPreviewing] = useState(false)
  const audio = useRef<HTMLAudioElement | null>(null)
  useEffect(() => () => audio.current?.pause(), [])

  const preview = async () => {
    audio.current?.pause()
    setPreviewing(true)
    try {
      const blob = await api.voicePreview(script.trim() || 'Every great video starts with a simple idea.', {
        engine: voice.engine,
        voice_id: voice.voice_id,
        speed,
        energy,
      })
      const el = new Audio(URL.createObjectURL(blob))
      audio.current = el
      el.onended = () => URL.revokeObjectURL(el.src)
      await el.play()
    } catch (e) {
      toast('error', e instanceof Error ? e.message : 'Could not make the preview.')
    } finally {
      setPreviewing(false)
    }
  }

  const quality: Quality = speedQuality(speed)
  const current = voices.find((v) => v.engine === voice.engine && v.id === voice.voice_id)
  const own = voice.engine === 'chatterbox'

  return (
    <div className="step">
      <header className="step-head">
        <h1 className="display">How should it sound?</h1>
        <p className="lede">
          {current ? `${shortName(current.name)} reads your script. ` : ''}Set the mood, then press Listen to hear your
          first lines.
        </p>
      </header>

      <div className="card stack stack--lg">
        <div className="field">
          <span className="field__label">Energy</span>
          <Segmented
            label="Energy"
            value={energyId(energy)}
            onChange={(id) => patch({ energy: ENERGY.find((e) => e.id === id)?.value ?? 0.5 })}
            items={ENERGY.map((e) => ({ id: e.id, label: e.label }))}
          />
          <p className="field__hint">
            {own
              ? 'Your own voice follows this closely: Hype sounds clearly more excited.'
              : 'A small change with AI voices. It makes a big difference with your own voice.'}
          </p>
        </div>

        {targetSeconds ? (
          <p className="note">
            The speed is set for you, so the video lasts exactly {formatDuration(targetSeconds)}. To choose the speed
            yourself, pick Natural length on the Length step.
          </p>
        ) : (
          <div className="speed">
            <Slider
              label="Speed"
              value={speed}
              min={0.5}
              max={2}
              step={0.05}
              onChange={(v) => patch({ speed: v })}
              format={(v) => `${v.toFixed(2)}×`}
            />
            <div className="speed__quality">
              <QualityBadge quality={quality} />
              {speed !== 1 && (
                <button type="button" className="link-btn" onClick={() => patch({ speed: 1 })}>
                  Reset to normal
                </button>
              )}
            </div>
          </div>
        )}

        <div className="listen">
          <Button variant="primary" busy={previewing} onClick={preview} disabled={!health?.ffmpeg}>
            {!previewing && <PlayIcon playing={false} />}
            Listen
          </Button>
          <span className="field__hint">
            {!health?.ffmpeg
              ? 'Needs ffmpeg, which is not installed.'
              : previewing && own
                ? 'Your own voice takes a little longer to prepare.'
                : 'Reads the start of your script with these settings.'}
          </span>
        </div>
      </div>
    </div>
  )
}
