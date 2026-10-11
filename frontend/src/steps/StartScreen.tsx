import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { Logo } from '../components/Shell'
import { readProjectFile } from '../lib/projectFile'
import { useDraft } from '../state/project'
import { useSession } from '../state/session'
import { ModelFolder } from './ModelFolder'

function firstWords(text: string, count = 12): string {
  const words = text.trim().split(/\s+/)
  return words.slice(0, count).join(' ') + (words.length > count ? '…' : '')
}

/** The first question: start fresh, carry on, or open a saved project. */
export function StartScreen() {
  const navigate = useNavigate()
  const script = useDraft((s) => s.script)
  const reset = useDraft((s) => s.reset)
  const load = useDraft((s) => s.load)
  const { start, setJob, toast } = useSession()
  const fileRef = useRef<HTMLInputElement>(null)
  const [opening, setOpening] = useState(false)
  // first run: ask where downloads and videos go before anything lands on the system drive
  // (not the whole catalog: checking the voice engines takes seconds)
  const [local, setLocal] = useState(false)
  const [folderAsking, setFolderAsking] = useState(false)
  useEffect(() => {
    api
      .health()
      .then((h) => setLocal(!h.demo))
      .catch(() => setLocal(false))
  }, [])
  const hasDraft = !!script.trim()
  const words = hasDraft ? script.trim().split(/\s+/).length : 0

  const fresh = () => {
    reset()
    setJob(null, null)
    start()
    navigate('/script')
  }

  const open = async (file: File) => {
    setOpening(true)
    try {
      load(await readProjectFile(file))
      setJob(null, null)
      start()
      toast('success', `Opened ${file.name}. Check your choices, then make the video.`)
      navigate('/export')
    } catch (e) {
      toast('error', e instanceof Error ? e.message : 'That file is not a NarraReel project.')
    } finally {
      setOpening(false)
    }
  }

  return (
    <div className="start">
      <header className="nav">
        <div className="nav__inner">
          <Logo />
        </div>
      </header>
      <main id="main" className="start__main">
        <div className="start__head">
          <h1 className="display">Turn your script into a captioned video</h1>
          <p className="lede">Write what to say, pick a voice, style the captions. NarraReel does the rest.</p>
        </div>

        {local && <ModelFolder onAsking={setFolderAsking} />}

        {!folderAsking && (
          <div className="start__choices">
            <button type="button" className="start-card start-card--primary" onClick={fresh}>
              <span className="start-card__title">Start a new video</span>
              <span className="start-card__text">Begin with an empty script.</span>
              <span className="start-card__go" aria-hidden="true">
                →
              </span>
            </button>

            {hasDraft && (
              <button
                type="button"
                className="start-card"
                onClick={() => {
                  start()
                  navigate('/script')
                }}
              >
                <span className="start-card__title">Continue where you left off</span>
                <span className="start-card__text">
                  “{firstWords(script)}” <span className="start-card__meta">{words} words</span>
                </span>
                <span className="start-card__go" aria-hidden="true">
                  →
                </span>
              </button>
            )}

            <button type="button" className="start-card" disabled={opening} onClick={() => fileRef.current?.click()}>
              <span className="start-card__title">{opening ? 'Opening…' : 'Open a saved project'}</span>
              <span className="start-card__text">A .narrareel.json file you saved after making a video.</span>
              <span className="start-card__go" aria-hidden="true">
                →
              </span>
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".json,application/json"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) void open(f)
                e.target.value = ''
              }}
            />
          </div>
        )}
      </main>
    </div>
  )
}
