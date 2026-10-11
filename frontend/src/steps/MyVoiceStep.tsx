import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { create } from 'zustand'
import { api, customVoiceUrl, watchJob } from '../api/client'
import type { QualityReport, VoiceProfile } from '../api/types'
import { Badge, Banner, Button, CodeWindow, ProgressBar, Tabs } from '../components/ui'
import { useRecorder } from '../hooks/useRecorder'
import { useCatalog } from '../state/catalog'
import { useDraft } from '../state/project'
import { useSession } from '../state/session'
import { ModelFolder } from './ModelFolder'
import { PlayIcon } from './VoiceStep'

type Tone = 'energetic' | 'calm' | 'hindi'
/** One question at a time: set up once, then pick a saved voice or record a new one in three short stages. */
type Stage = 'setup' | 'pick' | 'record' | 'check' | 'name'

const TONES: { id: Tone; label: string; language: string }[] = [
  { id: 'energetic', label: 'Energetic', language: 'en' },
  { id: 'calm', label: 'Calm', language: 'en' },
  { id: 'hindi', label: 'Hindi', language: 'hi' },
]

const STATUS_TONE = { ok: 'good', warn: 'warn', fail: 'bad' } as const
const STATUS_WORD = { ok: 'Good', warn: 'Check', fail: 'Fix' } as const

const RECORD_STAGES: { id: Stage; label: string }[] = [
  { id: 'record', label: 'Read aloud' },
  { id: 'check', label: 'Listen back' },
  { id: 'name', label: 'Name it' },
]

function mmss(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

// Lives outside the component so the progress survives leaving the page while the install runs.
const useInstall = create<{ progress: { fraction: number; message: string } | null }>(() => ({ progress: null }))

function startInstall() {
  const { toast } = useSession.getState()
  const { refreshEngines, refreshVoices } = useCatalog.getState()
  const finish = (message: string | null, error?: string) => {
    useInstall.setState({ progress: null })
    if (error) toast('error', error)
    else if (message) toast('success', message)
  }
  useInstall.setState({ progress: { fraction: 0, message: 'Starting' } })
  api
    .installEngine('chatterbox')
    .then(({ task_id }) =>
      watchJob(
        task_id,
        (e) => useInstall.setState({ progress: { fraction: e.fraction, message: e.message } }),
        async (status) => {
          if (status.status === 'done') {
            await Promise.all([refreshEngines(), refreshVoices()])
            finish('Voice cloning is ready.')
          } else finish(null, status.error ?? 'The setup did not finish.')
        },
        () => finish(null, 'Lost connection to NarraReel during setup. Reload the page and try again.'),
        'tasks',
      ),
    )
    .catch((e: unknown) => finish(null, e instanceof Error ? e.message : 'Could not start the setup.'))
}

function Substeps({ stage }: { stage: Stage }) {
  const at = RECORD_STAGES.findIndex((s) => s.id === stage)
  if (at < 0) return null
  return (
    <ol className="substeps" aria-label={`Step ${at + 1} of ${RECORD_STAGES.length}`}>
      {RECORD_STAGES.map((s, i) => (
        <li key={s.id} className={i < at ? 'substep substep--done' : i === at ? 'substep substep--now' : 'substep'}>
          <span className="substep__dot" aria-hidden="true">
            {i + 1}
          </span>
          {s.label}
        </li>
      ))}
    </ol>
  )
}

function QualityList({ report }: { report: QualityReport }) {
  return (
    <ul className="quality" aria-label="Recording check">
      {report.checks.map((c) => (
        <li key={c.id} className="quality__row">
          <Badge tone={STATUS_TONE[c.status]}>{STATUS_WORD[c.status]}</Badge>
          <span>
            <strong>{c.label}</strong> <span className="muted">{c.detail}</span>
          </span>
        </li>
      ))}
    </ul>
  )
}

/** A slim reminder while the one-time setup runs in the background. */
function InstallProgress() {
  const progress = useInstall((s) => s.progress)
  if (!progress) return null
  return (
    <div className="install-strip" role="status">
      <span>Setting up voice cloning: {progress.message}</span>
      <ProgressBar fraction={progress.fraction} label="Setup progress" />
    </div>
  )
}

export function MyVoiceStep() {
  const engine = useCatalog((s) => s.engines.find((e) => e.id === 'chatterbox'))
  const refreshVoices = useCatalog((s) => s.refreshVoices)
  const { voice, patch } = useDraft()
  const toast = useSession((s) => s.toast)
  const installing = useInstall((s) => !!s.progress)
  const available = !!engine?.status.available

  const [profiles, setProfiles] = useState<VoiceProfile[] | null>(null)
  const [stage, setStage] = useState<Stage | null>(null)
  const [folderAsking, setFolderAsking] = useState(false)

  const rec = useRecorder()
  const [tone, setTone] = useState<Tone>('energetic')
  const [guided, setGuided] = useState<Record<string, string>>({})
  const [report, setReport] = useState<QualityReport | null>(null)
  const [checking, setChecking] = useState(false)
  const [name, setName] = useState('')
  const [consent, setConsent] = useState(false)
  const [saving, setSaving] = useState(false)
  const [confirming, setConfirming] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const audio = useRef<HTMLAudioElement | null>(null)
  const [playingId, setPlayingId] = useState<string | null>(null)

  const reload = useCallback(
    () =>
      api
        .customVoices()
        .then((p) => {
          setProfiles(p)
          return p
        })
        .catch(() => {
          setProfiles([])
          return [] as VoiceProfile[]
        }),
    [],
  )

  useEffect(() => {
    void reload()
    api.guidedText().then(setGuided).catch(() => {})
    return () => audio.current?.pause()
  }, [reload])

  // decide the first question once we know what is already on this computer
  useEffect(() => {
    if (stage !== null || profiles === null) return
    if (!available && !installing) setStage('setup')
    else if (profiles.length > 0) setStage('pick')
    else setStage('record')
  }, [stage, profiles, available, installing])

  // someone who picks "My own voice" with exactly one saved voice means that one
  useEffect(() => {
    if (profiles?.length === 1 && voice.engine !== 'chatterbox') {
      patch({ voice: { engine: 'chatterbox', voice_id: profiles[0].id } })
    }
    // only when the list arrives, not every time the choice changes
  }, [profiles])

  // a finished recording moves straight on to the check
  useEffect(() => {
    if (!rec.blob) {
      setReport(null)
      return
    }
    setStage('check')
    let live = true
    setChecking(true)
    api
      .checkRecording(rec.blob)
      .then((r) => live && setReport(r))
      .catch((e: unknown) => {
        if (!live) return
        setReport(null)
        toast('error', e instanceof Error ? e.message : 'Could not check the recording.')
      })
      .finally(() => live && setChecking(false))
    return () => {
      live = false
    }
  }, [rec.blob, toast])

  const playback = useMemo(() => (rec.blob ? URL.createObjectURL(rec.blob) : null), [rec.blob])
  useEffect(() => () => (playback ? URL.revokeObjectURL(playback) : undefined), [playback])

  const playProfile = (p: VoiceProfile) => {
    audio.current?.pause()
    if (playingId === p.id) {
      setPlayingId(null)
      return
    }
    const el = new Audio(customVoiceUrl(p.id, 'reference.mp3'))
    audio.current = el
    setPlayingId(p.id)
    el.onended = () => setPlayingId(null)
    void el.play().catch(() => {
      setPlayingId(null)
      toast('error', 'Could not play that recording.')
    })
  }

  const remove = async (p: VoiceProfile) => {
    try {
      await api.deleteVoice(p.id)
      if (voice.engine === 'chatterbox' && voice.voice_id === p.id) {
        patch({ voice: { engine: 'edge', voice_id: 'en-US-AvaNeural' } })
      }
      setConfirming(null)
      const left = await reload()
      void refreshVoices()
      if (left.length === 0) setStage('record')
      toast('success', `Deleted “${p.name}”. Its recording is gone from this computer.`)
    } catch (e) {
      toast('error', e instanceof Error ? e.message : 'Could not delete that voice.')
    }
  }

  const recordNew = () => {
    rec.reset()
    setReport(null)
    setStage('record')
  }

  const language = TONES.find((t) => t.id === tone)?.language ?? 'en'
  const save = async () => {
    if (!rec.blob) return
    setSaving(true)
    try {
      const r = await api.cloneVoice(rec.blob, name.trim(), consent, language)
      patch({ voice: { engine: 'chatterbox', voice_id: r.profile.id } })
      setName('')
      setConsent(false)
      rec.reset()
      await reload()
      void refreshVoices()
      setStage('pick')
      toast('success', `Saved “${r.profile.name}” and chose it for this video.`)
    } catch (e) {
      toast('error', e instanceof Error ? e.message : 'Could not save the voice.')
    } finally {
      setSaving(false)
    }
  }

  if (stage === null) return <p className="loading">Loading…</p>

  const recording = rec.state === 'recording'
  const canSave = !!report?.usable && !!name.trim() && consent && !saving
  const hasProfiles = !!profiles && profiles.length > 0

  /* ---------- 0. one-time setup ---------- */
  if (stage === 'setup') {
    return (
      <div className="step">
        <header className="step-head">
          <h1 className="display">Set up your own voice</h1>
          <p className="lede">This happens once. After that, every video can speak in your voice.</p>
        </header>

        <ModelFolder onAsking={setFolderAsking} />

        {!folderAsking && (
          <div className="card stack">
            <h2 className="title">Turn on voice cloning</h2>
            <p className="muted">
              One click. NarraReel downloads what it needs to speak like you, about 3 GB, so it can take several
              minutes. You can record your voice while you wait.
            </p>
            {installing ? (
              <>
                <InstallProgress />
                <div className="row">
                  <Button variant="primary" onClick={() => setStage(hasProfiles ? 'pick' : 'record')}>
                    Record your voice while you wait
                  </Button>
                </div>
              </>
            ) : (
              <div className="row">
                <Button variant="primary" onClick={startInstall}>
                  Set up voice cloning
                </Button>
              </div>
            )}
            <details>
              <summary className="field__hint">Rather use the terminal?</summary>
              <CodeWindow title="Terminal">{'pip install "narrareel[clone]"'}</CodeWindow>
            </details>
          </div>
        )}
      </div>
    )
  }

  /* ---------- pick a saved voice ---------- */
  if (stage === 'pick') {
    return (
      <div className="step">
        <header className="step-head">
          <h1 className="display">Pick your voice</h1>
          <p className="lede">These are the voices you have saved on this computer. Click one to use it.</p>
        </header>
        <InstallProgress />

        <ul className="saved-list" role="radiogroup" aria-label="Your saved voices">
          {(profiles ?? []).map((p) => {
            const on = voice.engine === 'chatterbox' && voice.voice_id === p.id
            return (
              <li key={p.id} className={`vtile saved ${on ? 'vtile--on' : ''}`}>
                <button
                  type="button"
                  className={`vtile__play ${playingId === p.id ? 'vtile__play--on' : ''}`}
                  onClick={() => playProfile(p)}
                  aria-label={`${playingId === p.id ? 'Stop' : 'Play'} the recording of ${p.name}`}
                >
                  <PlayIcon playing={playingId === p.id} />
                </button>
                <button
                  type="button"
                  role="radio"
                  aria-checked={on}
                  className="vtile__pick"
                  onClick={() => patch({ voice: { engine: 'chatterbox', voice_id: p.id } })}
                >
                  <span className="vtile__name">{p.name}</span>
                  <span className="vtile__meta">
                    {{ en: 'English', hi: 'Hindi' }[p.language] ?? p.language}, saved {p.created_at.slice(0, 10)}
                  </span>
                </button>
                {confirming === p.id ? (
                  <span className="saved__confirm">
                    <Button variant="text" onClick={() => setConfirming(null)}>
                      Keep
                    </Button>
                    <Button variant="secondary" onClick={() => void remove(p)}>
                      Delete for good
                    </Button>
                  </span>
                ) : (
                  <Button variant="text" className="saved__delete" onClick={() => setConfirming(p.id)}>
                    Delete
                  </Button>
                )}
              </li>
            )
          })}
        </ul>

        <div className="center">
          <Button variant="secondary" onClick={recordNew}>
            Record a new voice
          </Button>
        </div>

        <details className="disclosure">
          <summary className="disclosure__summary">
            <span>Where NarraReel keeps its files</span>
          </summary>
          <div className="disclosure__body">
            <ModelFolder />
          </div>
        </details>
      </div>
    )
  }

  /* ---------- 1. read aloud ---------- */
  if (stage === 'record') {
    const cantRecord = rec.state === 'unsupported' || !!rec.error
    return (
      <div className="step">
        <Substeps stage={stage} />
        <header className="step-head">
          <h1 className="display">Read this aloud</h1>
          <p className="lede">
            Read it the way you want your videos to sound, in a quiet room. It takes about 20 seconds. The recording
            stays on this computer.
          </p>
        </header>
        <InstallProgress />

        <div className="card stack stack--lg">
          <div className="stack">
            <span className="field__label">Reading style</span>
            <Tabs label="Reading style" value={tone} onChange={setTone} items={TONES.map((t) => ({ id: t.id, label: t.label }))} />
            <blockquote className="guided" lang={language}>
              {guided[tone] ?? '…'}
            </blockquote>
          </div>

          {rec.state === 'unsupported' && (
            <Banner tone="warn" title="This browser can't record">
              Recording needs a modern browser and a secure page (https or localhost). You can upload a recording of
              yourself reading the paragraph instead.
            </Banner>
          )}
          {rec.error && <Banner tone="error">{rec.error}</Banner>}

          <div className="record-bar">
            {recording ? (
              <>
                <Button variant="primary" className="btn--lg" onClick={rec.stop}>
                  <span className="rec-dot rec-dot--stop" aria-hidden="true" />
                  Stop recording
                </Button>
                <span className="recording" role="status">
                  <span className="meter" aria-hidden="true">
                    <span className="meter__fill" style={{ transform: `scaleX(${rec.level})` }} />
                  </span>
                  {mmss(rec.seconds)}
                </span>
              </>
            ) : (
              rec.state !== 'unsupported' && (
                <Button variant="primary" className="btn--lg" busy={rec.state === 'asking'} onClick={() => void rec.start()}>
                  <span className="rec-dot" aria-hidden="true" />
                  Start recording
                </Button>
              )
            )}
            {cantRecord && !recording && (
              <>
                <input
                  ref={fileRef}
                  type="file"
                  accept="audio/*,.wav,.mp3,.m4a,.webm,.ogg,.flac"
                  hidden
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    if (f) rec.load(f)
                    e.target.value = ''
                  }}
                />
                <Button variant="secondary" onClick={() => fileRef.current?.click()}>
                  Upload a recording instead
                </Button>
              </>
            )}
          </div>
        </div>

        {hasProfiles && !recording && (
          <div className="center">
            <button type="button" className="link-btn" onClick={() => setStage('pick')}>
              Use a voice I already saved
            </button>
          </div>
        )}
      </div>
    )
  }

  /* ---------- 2. listen back ---------- */
  if (stage === 'check') {
    return (
      <div className="step">
        <Substeps stage={stage} />
        <header className="step-head">
          <h1 className="display">How did it go?</h1>
          <p className="lede">Listen back. NarraReel also checks the recording for you.</p>
        </header>

        <div className="card stack stack--lg">
          {playback && <audio className="player-audio" controls src={playback} />}
          {checking && <p className="muted">Checking the recording…</p>}
          {report && <QualityList report={report} />}
          {report && !report.usable && (
            <Banner tone="error" title="This recording can't be used yet">
              Fix the items marked “Fix”, then record again.
            </Banner>
          )}
          <div className="row row--end">
            <Button variant="secondary" onClick={recordNew}>
              Record again
            </Button>
            <Button variant="primary" disabled={!report?.usable} onClick={() => setStage('name')}>
              Sounds good, continue
            </Button>
          </div>
        </div>
      </div>
    )
  }

  /* ---------- 3. name it ---------- */
  return (
    <div className="step">
      <Substeps stage={stage} />
      <header className="step-head">
        <h1 className="display">Name your voice</h1>
        <p className="lede">Pick a name you will recognise later, then confirm the voice is yours to use.</p>
      </header>

      <form
        className="card stack stack--lg"
        onSubmit={(e) => {
          e.preventDefault()
          if (canSave) void save()
        }}
      >
        <div className="field">
          <label className="field__label" htmlFor="voice-name">
            Name
          </label>
          <input
            id="voice-name"
            className="input"
            value={name}
            maxLength={60}
            autoFocus
            placeholder={tone === 'calm' ? 'My calm voice' : tone === 'hindi' ? 'My Hindi voice' : 'My energetic voice'}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <label className="consent">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
          <span>
            This is my voice, or I have explicit permission from the person whose voice this is. I won&rsquo;t use it
            to impersonate or deceive anyone.
          </span>
        </label>
        <div className="row row--end">
          <Button variant="text" onClick={() => setStage('check')}>
            Back
          </Button>
          <Button variant="primary" type="submit" busy={saving} disabled={!canSave}>
            Save my voice
          </Button>
        </div>
      </form>
    </div>
  )
}
