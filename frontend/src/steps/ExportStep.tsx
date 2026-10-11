import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link, useNavigate } from 'react-router-dom'
import { api, jobFileUrl, watchJob } from '../api/client'
import { Banner, Button, CodeWindow, ProgressBar, Segmented } from '../components/ui'
import { formatDuration, slugFirstWords } from '../lib/time'
import { useCatalog } from '../state/catalog'
import { toProject, useDraft, voiceKey } from '../state/project'
import type { Draft } from '../state/project'
import { useSession } from '../state/session'

const STAGES: { id: string; label: string }[] = [
  { id: 'prepare', label: 'Getting ready' },
  { id: 'voice', label: 'Recording the voice' },
  { id: 'timing', label: 'Timing every word' },
  { id: 'captions', label: 'Adding captions' },
  { id: 'render', label: 'Putting the video together' },
]

const OTHER_FILES: { key: string; label: string; note: string }[] = [
  { key: 'audio_mp3', label: 'Voiceover (MP3)', note: 'The narration on its own' },
  { key: 'audio_wav', label: 'Voiceover (WAV)', note: 'Best quality, for video editors' },
  { key: 'captions_srt', label: 'Subtitles (SRT)', note: 'For YouTube and most editors' },
  { key: 'captions_ass', label: 'Styled subtitles (ASS)', note: 'Keeps your caption style' },
  { key: 'words_json', label: 'Word timings (JSON)', note: 'When every word starts and ends' },
  { key: 'project', label: 'Project file', note: 'Open it later to keep editing' },
]

function cliCommand(d: Draft): string {
  const parts = ['narrareel make script.txt', `--voice ${d.voice.engine}:${d.voice.voice_id}`]
  if (d.targetSeconds) parts.push(`--target ${Math.round(d.targetSeconds)}s`)
  else if (d.speed !== 1) parts.push(`--speed ${d.speed}`)
  if (d.energy !== 0.5) parts.push(`--energy ${d.energy}`)
  parts.push(`--format ${d.format}`, `--style ${d.captions.preset}`)
  if (d.captions.font) parts.push(`--font ${d.captions.font}`)
  if (d.background.type === 'transparent') parts.push('--background transparent')
  else if (d.background.type === 'solid' && d.background.color.toLowerCase() !== '#101010') parts.push(`--background "${d.background.color}"`)
  parts.push(`-o ${slugFirstWords(d.script)}.${d.export.video}`)
  return parts.join(' \\\n  ')
}

export function ExportStep() {
  const draft = useDraft()
  const { setExport } = draft
  const formats = useCatalog((s) => s.formats)
  const voices = useCatalog((s) => s.voices)
  const styles = useCatalog((s) => s.styles)
  const fonts = useCatalog((s) => s.fonts)
  const health = useCatalog((s) => s.health)
  const { job, jobVoiceKey, progress, setJob, setProgress, toast } = useSession()
  const navigate = useNavigate()
  const [running, setRunning] = useState<string | null>(null)
  const stop = useRef<(() => void) | null>(null)
  const fmt = formats.find((f) => f.id === draft.format)
  const isAudio = fmt ? !fmt.width : false
  const transparent = draft.background.type === 'transparent'
  const key = voiceKey(draft)
  const canReuse = !!job && job.status === 'done' && jobVoiceKey === key && !!job.result?.files.words_json
  useEffect(() => () => stop.current?.(), [])

  const run = async () => {
    const project = toProject(draft)
    setProgress({ stage: 'prepare', fraction: 0, message: 'Starting' })
    try {
      const created = canReuse && job ? await api.rerender(job.id, project) : await api.createJob(project)
      const id = created.job_id
      setRunning(id)
      stop.current = watchJob(
        id,
        (e) => setProgress({ stage: e.stage, fraction: e.fraction, message: e.message }),
        async () => {
          const status = await api.job(id)
          setRunning(null)
          setProgress(null)
          if (status.status === 'done') {
            setJob(status, key)
            toast('success', 'Your video is ready.')
          } else if (status.status === 'cancelled') {
            toast('info', 'Stopped. Nothing was saved.')
          } else {
            setJob(null, null)
            toast('error', status.error ?? 'The video could not be made.')
          }
        },
        () => {
          setRunning(null)
          setProgress(null)
          toast('error', 'Lost connection to NarraReel. Check that it is still running, then try again.')
        },
      )
    } catch (e) {
      setRunning(null)
      setProgress(null)
      toast('error', e instanceof Error ? e.message : 'Could not start the video.')
    }
  }

  const cancel = async () => {
    if (running) await api.cancelJob(running).catch(() => {})
  }

  const missingScript = !draft.script.trim()
  const busy = running !== null
  const stageIndex = progress ? Math.max(0, STAGES.findIndex((s) => s.id === progress.stage)) : 0
  const result = job?.status === 'done' ? job.result : null
  const files = result?.files ?? {}
  const others = OTHER_FILES.filter((d) => files[d.key])

  const hint = missingScript
    ? 'Add a script first.'
    : canReuse
      ? 'Only the captions changed, so the voice is reused and this is quick.'
      : isAudio
        ? 'You get the voiceover and subtitle files.'
        : 'Making a short video usually takes under a minute.'
  const actionLabel = result ? 'Make again' : isAudio ? 'Make my audio' : 'Make my video'
  // once something is made, getting it out is the main job
  const mainFile = files.video ?? files.audio_mp3
  const downloadUrl = job && mainFile ? jobFileUrl(job.id, mainFile, true) : null

  const voiceName = voices.find((v) => v.engine === draft.voice.engine && v.id === draft.voice.voice_id)?.name ?? draft.voice.voice_id
  const styleName = styles.find((s) => s.id === draft.captions.preset)?.name ?? draft.captions.preset
  const fontName = draft.captions.font ? (fonts.find((f) => f.id === draft.captions.font)?.name ?? draft.captions.font) : null
  const words = draft.script.trim() ? draft.script.trim().split(/\s+/).length : 0
  const backgroundName = {
    solid: 'Plain colour',
    transparent: 'See-through',
    image: draft.background.fileName ?? 'Picture',
    video: draft.background.fileName ?? 'Video',
  }[draft.background.type]

  const checklist = [
    { label: 'Script', value: words ? `${words} words` : 'Not written yet', to: '/script', missing: !words },
    { label: 'Length', value: draft.targetSeconds ? `Exactly ${formatDuration(draft.targetSeconds)}` : 'Natural length', to: '/script' },
    { label: 'Voice', value: voiceName, to: '/voice' },
    { label: 'Captions', value: fontName ? `${styleName}, in ${fontName}` : styleName, to: '/captions' },
    { label: 'Shape', value: fmt?.name ?? draft.format, to: '/captions' },
    ...(isAudio ? [] : [{ label: 'Background', value: backgroundName, to: '/captions' }]),
  ]

  // the bottom bar carries the forward action on every step; here that action is making the video
  const bar = createPortal(
    <div className="step-nav">
      <div className="step-nav__inner">
        <Button variant="text" onClick={() => navigate('/captions')}>
          Back
        </Button>
        <div className="step-nav__next">
          {busy ? (
            <Button variant="secondary" className="btn--lg" onClick={cancel}>
              Stop
            </Button>
          ) : (
            <Button
              variant={downloadUrl ? 'secondary' : 'primary'}
              className="btn--lg"
              disabled={missingScript || (health ? !health.ffmpeg : false)}
              onClick={() => {
                window.scrollTo({ top: 0 })
                void run()
              }}
            >
              {actionLabel}
            </Button>
          )}
          {downloadUrl && !busy && (
            <a className="btn btn--primary btn--lg" href={downloadUrl} download>
              Download<span className="hide-phone">{isAudio ? ' audio' : ' video'}</span>
            </a>
          )}
        </div>
      </div>
    </div>,
    document.body,
  )

  return (
    <div className="step">
      {bar}
      <header className="step-head">
        <h1 className="display">
          {busy ? 'Making your video' : result ? 'Your video is ready' : 'Ready to make your video?'}
        </h1>
        <p className="lede">
          {busy
            ? 'You can watch the progress here. Stop at any time from the bar below.'
            : result
              ? 'Watch it here, then download it. Change anything and make it again whenever you like.'
              : 'Check your choices below. Click any of them to change it.'}
        </p>
      </header>

      {busy && progress && (
        <section className="make" aria-label="Making your video" aria-live="polite">
          <h2 className="make__title">{STAGES[stageIndex]?.label ?? 'Working'}…</h2>
          <ProgressBar fraction={progress.fraction} label="Video progress" />
          <ol className="stages" aria-label="Progress">
            {STAGES.map((s, i) => (
              <li key={s.id} className={i < stageIndex ? 'stage stage--done' : i === stageIndex ? 'stage stage--now' : 'stage'}>
                {s.label}
              </li>
            ))}
          </ol>
          <p className="make__line">{progress.message}. Keep this tab open.</p>
        </section>
      )}

      {health && (!health.ffmpeg || (!health.libass && !isAudio)) && (
        <Banner tone="error" title={health.ffmpeg ? 'Your ffmpeg can’t draw captions' : 'ffmpeg is missing'}>
          NarraReel needs ffmpeg to make videos. Install it with <code>winget install Gyan.FFmpeg</code> on Windows,{' '}
          <code>brew install ffmpeg</code> on macOS or <code>sudo apt install ffmpeg</code> on Linux, then restart
          NarraReel.
        </Banner>
      )}

      {result && job && (
        <section className="result" aria-label="Your video">
          {result.target_seconds && (
            <p className="result__fit">
              {result.target_met
                ? `It lasts exactly ${formatDuration(result.duration)}, as you asked.`
                : `It lasts ${formatDuration(result.duration)}. Your target was ${formatDuration(result.target_seconds)}.`}
            </p>
          )}
          {result.note && <Banner tone="warn">{result.note}</Banner>}
          {result.warnings.map((w) => (
            <Banner key={w} tone="warn">{w}</Banner>
          ))}
          {files.video ? (
            <video className="player" controls preload="metadata" src={jobFileUrl(job.id, files.video)} />
          ) : (
            <audio className="player-audio" controls src={jobFileUrl(job.id, 'voice.mp3')} />
          )}

          {others.length > 0 && (
            <details className="disclosure">
              <summary className="disclosure__summary">
                <span>{files.video ? 'Other files' : 'Your files'}</span>
                <span className="disclosure__value">Voiceover, subtitles and more</span>
              </summary>
              <ul className="downloads">
                {others.map((d) => (
                  <li key={d.key} className="download">
                    <span className="download__text">
                      <strong>{d.label}</strong>
                      <span className="field__hint">{d.note}</span>
                    </span>
                    <a className="btn btn--secondary" href={jobFileUrl(job.id, files[d.key], true)} download>
                      Download
                    </a>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </section>
      )}

      <section className="section" aria-labelledby="choices-title">
        <h2 className="section__title" id="choices-title">
          Your choices
        </h2>
        <ul className="checklist">
          {checklist.map((c) => (
            <li key={c.label}>
              <Link to={c.to} className={`checklist__row ${c.missing ? 'checklist__row--missing' : ''}`}>
                <span className="checklist__label">{c.label}</span>
                <span className="checklist__value">{c.value}</span>
                <span className="checklist__edit">Change</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <p className="make-hint">{hint}</p>

      {!isAudio && (
        <details className="disclosure">
          <summary className="disclosure__summary">
            <span>More options</span>
            <span className="disclosure__value">
              {{ fast: 'Quick', balanced: 'Standard', high: 'Best quality' }[draft.export.quality]}
              {transparent ? `, ${draft.export.video === 'mov' ? 'MOV' : 'WebM'}` : ''}
            </span>
          </summary>
          <div className="disclosure__body stack stack--lg">
            <div className="field">
              <span className="field__label">Picture quality</span>
              <Segmented
                label="Render quality"
                value={draft.export.quality}
                onChange={(v) => setExport({ quality: v })}
                items={[
                  { id: 'fast', label: 'Quick' },
                  { id: 'balanced', label: 'Standard' },
                  { id: 'high', label: 'Best quality' },
                ]}
              />
              <p className="field__hint">Best quality looks sharper but takes longer to make.</p>
            </div>
            {transparent && (
              <div className="field">
                <span className="field__label">File type for the see-through video</span>
                <Segmented
                  label="Overlay file type"
                  value={draft.export.video === 'mov' ? 'mov' : 'webm'}
                  onChange={(v) => setExport({ video: v })}
                  items={[
                    { id: 'webm', label: 'WebM (small file)' },
                    { id: 'mov', label: 'MOV (works in every editor)' },
                  ]}
                />
                {draft.export.video === 'mov' && <p className="field__hint">MOV files are big: roughly 20 MB for every 10 seconds.</p>}
              </div>
            )}
          </div>
        </details>
      )}

      <details className="disclosure">
        <summary className="disclosure__summary">
          <span>Use the terminal instead</span>
          <span className="disclosure__value">For developers</span>
        </summary>
        <div className="disclosure__body">
          <CodeWindow title="Terminal">{cliCommand(draft)}</CodeWindow>
        </div>
      </details>
    </div>
  )
}
