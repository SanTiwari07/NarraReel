import { useEffect, useMemo, useRef, useState } from 'react'
import { create } from 'zustand'
import { api, customVoiceUrl, watchJob } from '../api/client'
import type { QualityReport, VoiceProfile } from '../api/types'
import { Badge, Banner, Button, Card, CodeWindow, Field, ProgressBar, Tabs } from '../components/ui'
import { useRecorder } from '../hooks/useRecorder'
import { useCatalog } from '../state/catalog'
import { useDraft } from '../state/project'
import { useSession } from '../state/session'
import { ModelFolder } from './ModelFolder'

type Tone = 'energetic' | 'calm' | 'hindi'

const TONES: { id: Tone; label: string; language: string }[] = [
  { id: 'energetic', label: 'Energetic', language: 'en' },
  { id: 'calm', label: 'Calm', language: 'en' },
  { id: 'hindi', label: 'Hindi', language: 'hi' },
]

const STATUS_TONE = { ok: 'good', warn: 'warn', fail: 'bad' } as const
const STATUS_WORD = { ok: 'Good', warn: 'Check', fail: 'Fix' } as const

function mmss(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

function SavedVoices({ onChange }: { onChange: () => void }) {
  const [profiles, setProfiles] = useState<VoiceProfile[] | null>(null)
  const [confirming, setConfirming] = useState<string | null>(null)
  const voice = useDraft((s) => s.voice)
  const patch = useDraft((s) => s.patch)
  const toast = useSession((s) => s.toast)
  const importRef = useRef<HTMLInputElement>(null)
  const audio = useRef<HTMLAudioElement | null>(null)

  const reload = () => api.customVoices().then(setProfiles).catch(() => setProfiles([]))
  useEffect(() => {
    void reload()
    return () => audio.current?.pause()
  }, [])
  // reload when a new voice is created elsewhere on the page
  useEffect(() => {
    const h = () => void reload()
    window.addEventListener('narrareel:voices-changed', h)
    return () => window.removeEventListener('narrareel:voices-changed', h)
  }, [])

  const play = (p: VoiceProfile) => {
    audio.current?.pause()
    audio.current = new Audio(customVoiceUrl(p.id, 'reference.mp3'))
    void audio.current.play().catch(() => toast('error', 'Could not play that recording.'))
  }

  const remove = async (p: VoiceProfile) => {
    try {
      await api.deleteVoice(p.id)
      if (voice.engine === 'chatterbox' && voice.voice_id === p.id) {
        patch({ voice: { engine: 'edge', voice_id: 'en-US-AvaNeural' } })
      }
      setConfirming(null)
      await reload()
      onChange()
      toast('success', `Deleted “${p.name}”. Its recording is gone from this computer.`)
    } catch (e) {
      toast('error', e instanceof Error ? e.message : 'Could not delete that voice.')
    }
  }

  const importFile = async (file: File) => {
    try {
      const p = await api.importVoice(file)
      await reload()
      onChange()
      toast('success', `Imported “${p.name}”.`)
    } catch (e) {
      toast('error', e instanceof Error ? e.message : 'Could not import that voice.')
    }
  }

  return (
    <Card className="stack" as="section">
      <div className="card-head">
        <h2 className="title">Your saved voices</h2>
        <input
          ref={importRef}
          type="file"
          accept=".zip,application/zip"
          hidden
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) void importFile(f)
            e.target.value = ''
          }}
        />
        <Button variant="secondary" onClick={() => importRef.current?.click()}>
          Import a voice file
        </Button>
      </div>
      {profiles === null ? (
        <p className="muted">Loading…</p>
      ) : profiles.length === 0 ? (
        <p className="muted">No voices yet. Record one below and it appears here.</p>
      ) : (
        <div className="voice-grid">
          {profiles.map((p) => {
            const on = voice.engine === 'chatterbox' && voice.voice_id === p.id
            return (
              <article key={p.id} className={`voice ${on ? 'voice--on' : ''}`}>
                <div className="voice__head">
                  <h3 className="voice__name">{p.name}</h3>
                  <Badge tone="good">Yours</Badge>
                </div>
                <p className="voice__meta">
                  {p.language}, {Math.round(p.duration)} s reference, saved {p.created_at.slice(0, 10)}
                </p>
                <div className="voice__actions">
                  <Button variant="text" onClick={() => play(p)} aria-label={`Play the recording of ${p.name}`}>
                    Play recording
                  </Button>
                  <Button
                    variant={on ? 'primary' : 'secondary'}
                    aria-pressed={on}
                    onClick={() => patch({ voice: { engine: 'chatterbox', voice_id: p.id } })}
                  >
                    {on ? 'Selected' : 'Use'}
                  </Button>
                </div>
                <div className="voice__actions">
                  <a className="btn btn--text" href={customVoiceUrl(p.id, 'export')} download>
                    Export
                  </a>
                  {confirming === p.id ? (
                    <span className="row">
                      <Button variant="text" onClick={() => setConfirming(null)}>
                        Keep
                      </Button>
                      <Button variant="secondary" onClick={() => void remove(p)}>
                        Delete for good
                      </Button>
                    </span>
                  ) : (
                    <Button variant="text" onClick={() => setConfirming(p.id)}>
                      Delete
                    </Button>
                  )}
                </div>
              </article>
            )
          })}
        </div>
      )}
    </Card>
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

function CloneFlow({ onCreated }: { onCreated: (p: VoiceProfile) => void }) {
  const rec = useRecorder()
  const toast = useSession((s) => s.toast)
  const [tone, setTone] = useState<Tone>('energetic')
  const [guided, setGuided] = useState<Record<string, string>>({})
  const [report, setReport] = useState<QualityReport | null>(null)
  const [checking, setChecking] = useState(false)
  const [name, setName] = useState('')
  const [consent, setConsent] = useState(false)
  const [saving, setSaving] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const playback = useMemo(() => (rec.blob ? URL.createObjectURL(rec.blob) : null), [rec.blob])
  useEffect(() => () => (playback ? URL.revokeObjectURL(playback) : undefined), [playback])
  useEffect(() => {
    api.guidedText().then(setGuided).catch(() => {})
  }, [])

  // check each new recording as soon as it exists
  useEffect(() => {
    if (!rec.blob) {
      setReport(null)
      return
    }
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

  const language = TONES.find((t) => t.id === tone)?.language ?? 'en'
  const save = async () => {
    if (!rec.blob) return
    setSaving(true)
    try {
      const r = await api.cloneVoice(rec.blob, name.trim(), consent, language)
      toast('success', `Saved “${r.profile.name}”. Select it to narrate with your voice.`)
      setName('')
      setConsent(false)
      rec.reset()
      onCreated(r.profile)
    } catch (e) {
      toast('error', e instanceof Error ? e.message : 'Could not save the voice.')
    } finally {
      setSaving(false)
    }
  }

  const recording = rec.state === 'recording'
  const canSave = !!report?.usable && !!name.trim() && consent && !saving

  return (
    <Card className="stack stack--lg" as="section">
      <div className="stack">
        <h2 className="title">Clone your voice</h2>
        <p className="muted">
          Your recording stays on this computer. Read the paragraph the way you want your videos to sound: the clone
          copies how you speak, not only how you sound.
        </p>
      </div>

      <div className="stack">
        <Tabs
          label="Guided paragraph"
          value={tone}
          onChange={setTone}
          items={TONES.map((t) => ({ id: t.id, label: t.label }))}
        />
        <blockquote className="guided" lang={language}>
          {guided[tone] ?? '…'}
        </blockquote>
      </div>

      {rec.state === 'unsupported' && (
        <Banner tone="warn" title="This browser can't record">
          Upload a recording instead. Recording needs a modern browser and a secure page (https or localhost).
        </Banner>
      )}
      {rec.error && <Banner tone="error">{rec.error}</Banner>}

      <div className="row">
        {!recording && rec.state !== 'unsupported' && (
          <Button variant="primary" busy={rec.state === 'asking'} onClick={() => void rec.start()}>
            {rec.blob ? 'Record again' : 'Start recording'}
          </Button>
        )}
        {recording && (
          <>
            <Button variant="primary" onClick={rec.stop}>
              Stop recording
            </Button>
            <span className="recording" role="status">
              <span className="meter" aria-hidden="true">
                <span className="meter__fill" style={{ transform: `scaleX(${rec.level})` }} />
              </span>
              {mmss(rec.seconds)}
            </span>
          </>
        )}
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
        {!recording && (
          <Button variant="secondary" onClick={() => fileRef.current?.click()}>
            Upload a recording
          </Button>
        )}
        {!recording && !rec.blob && <span className="field__hint">Aim for 15 to 30 seconds in a quiet room.</span>}
      </div>

      {rec.blob && (
        <div className="stack">
          {playback && <audio className="player-audio" controls src={playback} />}
          {checking && <p className="muted">Checking the recording…</p>}
          {report && <QualityList report={report} />}
          {report && !report.usable && (
            <Banner tone="error" title="This recording can't be used yet">
              Fix the items marked “Fix”, then record again.
            </Banner>
          )}
        </div>
      )}

      {report?.usable && (
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault()
            if (canSave) void save()
          }}
        >
          <Field label="Name this voice" htmlFor="voice-name">
            <input
              id="voice-name"
              className="input"
              value={name}
              maxLength={60}
              placeholder="My energetic voice"
              onChange={(e) => setName(e.target.value)}
            />
          </Field>
          <label className="consent">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            <span>
              This is my voice, or I have explicit permission from the person whose voice this is. I won&rsquo;t use
              it to impersonate or deceive anyone.
            </span>
          </label>
          <div>
            <Button variant="primary" type="submit" busy={saving} disabled={!canSave}>
              Save my voice
            </Button>
          </div>
        </form>
      )}
    </Card>
  )
}

// Lives outside the component so the progress survives switching tabs while the install runs.
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

function SetUpCloning() {
  const progress = useInstall((s) => s.progress)
  return (
    <Card className="stack">
      <h2 className="title">Turn on voice cloning</h2>
      <p className="muted">
        One click, one time. It downloads what NarraReel needs to speak in your voice: about 3 GB, so it can take
        several minutes. You can record your voice while you wait.
      </p>
      {progress ? (
        <>
          <ProgressBar fraction={progress.fraction} label="Setup progress" />
          <p className="field__hint">{progress.message}. Keep this window open.</p>
        </>
      ) : (
        <div>
          <Button variant="primary" onClick={startInstall}>
            Set up voice cloning
          </Button>
        </div>
      )}
      <details>
        <summary className="field__hint">Rather use the terminal?</summary>
        <CodeWindow title="Terminal">{'pip install "narrareel[clone]"'}</CodeWindow>
      </details>
    </Card>
  )
}

export function MyVoicePanel() {
  const engine = useCatalog((s) => s.engines.find((e) => e.id === 'chatterbox'))
  const refreshVoices = useCatalog((s) => s.refreshVoices)
  const energy = useDraft((s) => s.energy)
  const available = !!engine?.status.available

  const changed = () => {
    window.dispatchEvent(new Event('narrareel:voices-changed'))
    void refreshVoices()
  }

  return (
    <div className="stack stack--lg">
      <ModelFolder />
      {!available && <SetUpCloning />}
      <SavedVoices onChange={changed} />
      <CloneFlow onCreated={changed} />
      <p className="field__hint">
        Energy is set to {energy < 0.35 ? 'Calm' : energy > 0.65 ? 'Hype' : 'Normal'} below. With your own voice it
        changes how expressive the delivery is, not only how loud it is.
      </p>
    </div>
  )
}
