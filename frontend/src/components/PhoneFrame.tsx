import { useMemo, useState } from 'react'
import { usePreviewUrl } from '../hooks/useAsync'
import { toProject, useDraft } from '../state/project'
import { useCatalog } from '../state/catalog'
import { Switch } from './ui'

const SAMPLE = 'This is how your captions will look. Every word lands exactly when it is spoken.'

/** The frame shows an early caption, so only the opening words matter; typing further down
 * the script does not re-render it. */
function opening(script: string): string {
  const text = script.trim()
  if (text.length <= 240) return text
  const cut = text.slice(0, 240)
  return cut.slice(0, cut.lastIndexOf(' ') > 0 ? cut.lastIndexOf(' ') : 240)
}

/** The live caption frame: the real renderer's output for the user's own script and style. */
export function PhoneFrame() {
  const draft = useDraft()
  const format = useCatalog((s) => s.formats.find((f) => f.id === draft.format))
  const [zones, setZones] = useState(false)
  const usingSample = !draft.script.trim()
  const head = usingSample ? SAMPLE : opening(draft.script)

  const project = useMemo(() => toProject({ ...draft, script: head }), [draft, head])

  const isVideo = !!format?.width
  const { url, error, loading } = usePreviewUrl(project, isVideo)
  const ratio = format?.width && format.height ? `${format.width} / ${format.height}` : '9 / 16'
  const landscape = !!format?.width && !!format.height && format.width > format.height

  return (
    <figure className="preview" aria-label="Caption preview">
      {isVideo ? (
        <>
          <div
            className={`phone ${landscape ? 'phone--landscape' : ''}`}
            style={{ aspectRatio: ratio }}
            aria-busy={loading}
          >
            {url && <img className="phone__img" src={url} alt="A frame of your video with captions" />}
            {!url && !error && <div className="phone__placeholder">Drawing a frame…</div>}
            {zones && format && (
              <div className="phone__zones" aria-hidden="true">
                <span className="zone zone--top" style={{ height: `${(format.safe_zone.top ?? 0) * 100}%` }} />
                <span className="zone zone--bottom" style={{ height: `${(format.safe_zone.bottom ?? 0) * 100}%` }} />
                <span className="zone zone--right" style={{ width: `${(format.safe_zone.right ?? 0) * 100}%` }} />
              </div>
            )}
            {loading && url && <span className="phone__busy" aria-hidden="true" />}
          </div>
          <figcaption className="preview__meta">
            <span className="preview__note">
              {usingSample ? 'Sample words until you write your script' : 'A frame from your video'}
            </span>
            {format && format.id === 'reels' && (
              <Switch label="Show app buttons" checked={zones} onChange={setZones} />
            )}
          </figcaption>
          {error && <p className="preview__error">{error}</p>}
        </>
      ) : (
        <div className="phone phone--audio">
          <p>Audio only: you get the voiceover and subtitle files, so there is no picture to show.</p>
        </div>
      )}
    </figure>
  )
}
