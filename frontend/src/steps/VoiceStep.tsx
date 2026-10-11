import { useEffect, useMemo, useRef, useState } from 'react'
import { api, voiceSampleUrl, watchJob } from '../api/client'
import type { Quality, Voice } from '../api/types'
import { Button, CodeWindow, ProgressBar, QualityBadge, Segmented, Slider } from '../components/ui'
import { formatDuration, speedQuality } from '../lib/time'
import { useCatalog } from '../state/catalog'
import { useDraft } from '../state/project'
import { useScriptInfo } from '../state/scriptInfo'
import { useSession } from '../state/session'
import { MyVoicePanel } from './MyVoicePanel'

type Mode = 'ai' | 'mine'
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

/** "US, female" — some names already read "Heart (US, female)", so nothing is said twice. */
function voiceMeta(voice: Voice, showLanguage: boolean): string {
  const named = voice.accent != null && voice.name.includes(`(${voice.accent}`)
  const lang = LANGUAGE_NAMES[voice.language.split('-')[0]] ?? voice.language
  return [showLanguage ? lang : null, named ? null : voice.accent, named || voice.gender === 'unknown' ? null : voice.gender]
    .filter(Boolean)
    .join(', ')
}

function PlayIcon({ playing }: { playing: boolean }) {
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
        <span className="vtile__name">{voice.name.replace(/Multilingual$/, '')}</span>
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

export function VoiceStep() {
  const { voice, speed, energy, script, targetSeconds, patch } = useDraft()
  const voices = useCatalog((s) => s.voices)
  const health = useCatalog((s) => s.health)
  const { analysis } = useScriptInfo()
  const toast = useSession((s) => s.toast)
  const [mode, setMode] = useState<Mode>(voice.engine === 'chatterbox' ? 'mine' : 'ai')
  const [lang, setLang] = useState(analysis.data?.language_hint ?? 'en')
  const [gender, setGender] = useState<Gender>('all')
  const [limit, setLimit] = useState(PAGE)
  const [playing, setPlaying] = useState<string | null>(null)
  const [previewing, setPreviewing] = useState(false)
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

  const preview = async () => {
    stopAudio()
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
  const shown = filtered.slice(0, limit)
  const current = voices.find((v) => v.engine === voice.engine && v.id === voice.voice_id)

  return (
    <div className="step">
      <header className="step-head">
        <h1 className="display">Who should read it?</h1>
        <p className="lede">Press play to hear a voice, then pick the one that suits your video.</p>
      </header>

      <Segmented
        label="Voice source"
        value={mode}
        onChange={setMode}
        items={[
          { id: 'ai', label: 'Ready-made voices' },
          {
            id: 'mine',
            label: 'My own voice',
            disabled: !!health?.demo,
            hint: health?.demo ? 'Not available in the demo' : undefined,
          },
        ]}
      />

      {mode === 'mine' ? (
        <MyVoicePanel />
      ) : (
        <section className="section" aria-label="Ready-made voices">
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
              <span className="field__label">
                Sounds
              </span>
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
        </section>
      )}

      <section className="section" aria-labelledby="sound-title">
        <div className="section__head">
          <h2 className="section__title" id="sound-title">
            How should it sound?
          </h2>
          {current && <p className="section__hint">Voice: {current.name}</p>}
        </div>

        <div className="field">
          <span className="field__label">Energy</span>
          <Segmented
            label="Energy"
            value={energyId(energy)}
            onChange={(id) => patch({ energy: ENERGY.find((e) => e.id === id)?.value ?? 0.5 })}
            items={ENERGY.map((e) => ({ id: e.id, label: e.label }))}
          />
          <p className="field__hint">
            {voice.engine === 'chatterbox'
              ? 'Your own voice follows this closely.'
              : 'A small change with ready-made voices. It makes a big difference with your own voice.'}
          </p>
        </div>

        {targetSeconds ? (
          <p className="note">
            The speed is set for you, so the video lasts exactly {formatDuration(targetSeconds)}. To choose the speed
            yourself, pick Natural length on the Script step.
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
            Listen to your first lines
          </Button>
          <span className="field__hint">
            {health?.ffmpeg ? 'Reads the start of your script with these settings.' : 'Needs ffmpeg, which is not installed.'}
          </span>
        </div>
      </section>
    </div>
  )
}
