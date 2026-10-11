import { useEffect, useRef, useState } from 'react'
import { api, watchJob } from '../api/client'
import type { ModelStorage } from '../api/types'
import { Button, Card, ProgressBar } from '../components/ui'
import { useSession } from '../state/session'

const gb = (n: number) => `${n.toFixed(1)} GB`

/** Asks where the multi-GB voice model should live, before it lands on a full system drive. */
export function ModelFolder() {
  const toast = useSession((s) => s.toast)
  const [info, setInfo] = useState<ModelStorage | null>(null)
  const [open, setOpen] = useState(false)
  const [typing, setTyping] = useState(false)
  const [typed, setTyped] = useState('')
  const [picking, setPicking] = useState(false)
  const [progress, setProgress] = useState<{ fraction: number; message: string } | null>(null)
  const stop = useRef<(() => void) | null>(null)

  const reload = () =>
    api
      .modelStorage()
      .then(setInfo)
      .catch(() => setInfo(null))
  useEffect(() => {
    void reload()
    return () => stop.current?.()
  }, [])

  if (!info || info.from_env) return null

  const use = async (path: string) => {
    try {
      const { task_id } = await api.setModelFolder(path)
      setProgress({ fraction: 0, message: 'Starting' })
      stop.current = watchJob(
        task_id,
        (e) => setProgress({ fraction: e.fraction, message: e.message }),
        async (status) => {
          setProgress(null)
          await reload()
          if (status.status !== 'done') {
            toast('error', status.error ?? 'The folder could not be changed.')
            return
          }
          setOpen(false)
          setTyping(false)
          toast('success', `The voice model now lives in ${path}.`)
          const left = (status.result as { leftovers?: string[] } | null)?.leftovers ?? []
          if (left.length) {
            toast('info', `The old copy in ${left[0]} is still in use, so it was not deleted. Delete it after restarting NarraReel.`)
          }
        },
        () => {
          setProgress(null)
          toast('error', 'Lost connection to NarraReel while moving the model. Reload the page to see where it is.')
        },
        'tasks',
      )
    } catch (e) {
      toast('error', e instanceof Error ? e.message : 'That folder cannot be used.')
    }
  }

  const keep = async () => {
    try {
      setInfo(await api.keepModelFolder())
      toast('success', `The voice model stays in ${info.path}.`)
    } catch (e) {
      toast('error', e instanceof Error ? e.message : 'Could not save your choice.')
    }
  }

  const browse = async () => {
    setPicking(true)
    try {
      const { path } = await api.browseModelFolder()
      if (path) await use(path)
    } catch (e) {
      // no folder window on this computer (for example in Docker): let the person type it
      setTyping(true)
      toast('error', e instanceof Error ? e.message : 'The folder window could not open. Type the folder instead.')
    } finally {
      setPicking(false)
    }
  }

  const downloaded = info.models_gb >= 0.1
  const tight = info.free_gb !== null && !downloaded && info.free_gb < info.needed_gb + 1
  const asking = !info.chosen || open

  const controls = progress ? (
    <div className="stack">
      <ProgressBar fraction={progress.fraction} label="Moving the voice model" />
      <p className="field__hint">{progress.message}. Keep this window open.</p>
    </div>
  ) : (
    <>
      <div className="row">
        <Button variant="primary" busy={picking} onClick={browse}>
          {downloaded ? 'Move to another folder' : 'Choose a folder'}
        </Button>
        {!info.chosen && (
          <Button variant="secondary" disabled={picking} onClick={keep}>
            Keep it here
          </Button>
        )}
        {info.chosen && (
          <Button variant="text" onClick={() => setOpen(false)}>
            Cancel
          </Button>
        )}
        <button type="button" className="link-btn" onClick={() => setTyping((t) => !t)}>
          Type a folder instead
        </button>
      </div>
      {picking && <p className="field__hint">A folder window opened on this computer. It may be behind the browser.</p>}
      {typing && (
        <form
          className="inline-form"
          onSubmit={(e) => {
            e.preventDefault()
            if (typed.trim()) void use(typed.trim())
          }}
        >
          <div className="field field--grow">
            <label className="field__label" htmlFor="model-folder">
              Folder
            </label>
            <input
              id="model-folder"
              className="input"
              value={typed}
              placeholder="For example D:\NarraReel models"
              onChange={(e) => setTyped(e.target.value)}
            />
          </div>
          <Button variant="secondary" type="submit" disabled={!typed.trim()}>
            Use this folder
          </Button>
        </form>
      )}
    </>
  )

  if (!asking) {
    return (
      <div className="folder-row">
        <span className="folder-row__text">
          <span className="field__label">Voice model folder</span>
          <code className="folder-path">{info.path}</code>
          <span className="field__hint">
            {downloaded ? `${gb(info.models_gb)} downloaded` : 'Downloads on first use'}
            {info.free_gb !== null && `, ${gb(info.free_gb)} free`}
          </span>
        </span>
        <Button variant="secondary" onClick={() => setOpen(true)}>
          Change
        </Button>
      </div>
    )
  }

  return (
    <Card className="stack" as="section">
      <h2 className="title">Where should the voice model be kept?</h2>
      <p className="muted">
        {downloaded
          ? `The voice model takes ${gb(info.models_gb)}. It is in this folder now. Keep it there, or move it to a drive with more room.`
          : `Speaking in your own voice needs a model of about ${gb(info.needed_gb)}, downloaded once. Choose where it goes before it downloads.`}
      </p>
      <div className="folder-now">
        <code className="folder-path">{info.path}</code>
        {info.free_gb !== null && (
          <span className={tight ? 'field__hint field__hint--warn' : 'field__hint'}>
            {gb(info.free_gb)} free on this drive{tight ? '. That is not enough, so choose another drive.' : ''}
          </span>
        )}
      </div>
      {controls}
    </Card>
  )
}
