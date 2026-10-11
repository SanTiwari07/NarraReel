import { useRef, useState } from 'react'
import { formatDuration } from '../lib/time'
import { useDraft } from '../state/project'
import { useScriptInfo } from '../state/scriptInfo'
import { useSession } from '../state/session'
import { Banner, Button } from '../components/ui'
import { LengthSection } from './LengthSection'

const LONG_SENTENCE = 35

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

export function ScriptStep() {
  const { script, patch } = useDraft()
  const { analysis } = useScriptInfo()
  const toast = useSession((s) => s.toast)
  const fileRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const a = analysis.data

  const readFile = async (file: File) => {
    if (!/\.(txt|md|markdown)$/i.test(file.name) && !file.type.startsWith('text/')) {
      toast('error', 'Drop a .txt or .md file.')
      return
    }
    patch({ script: (await file.text()).replace(/^﻿/, '') })
  }

  const longest = a ? Math.max(...a.sentences.map((s) => s.seconds), 1) : 1

  return (
    <div className="step">
      <header className="step-head">
        <h1 className="display">What should your video say?</h1>
        <p className="lede">
          Type or paste the words to be spoken. Start a new line for each new idea. To make a word stand out in the
          captions, put *stars* around it.
        </p>
      </header>

      <div className={`script-box ${dragging ? 'script-box--drag' : ''}`}>
        <label htmlFor="script" className="sr-only">
          Script
        </label>
        <textarea
          id="script"
          className="script-input"
          value={script}
          spellCheck
          placeholder={'Wake up early.\nGrind hard.\nSuccess is waiting for you at the end of the road.'}
          onChange={(e) => patch({ script: e.target.value })}
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragging(false)
            const f = e.dataTransfer.files[0]
            if (f) void readFile(f)
          }}
        />
        <div className="script-box__foot">
          <p className="script-count" aria-live="polite">
            {a && a.word_count > 0 ? (
              <>
                <strong>{plural(a.word_count, 'word')}</strong> in {plural(a.sentence_count, 'sentence')}. About{' '}
                <strong>{formatDuration(a.estimate.total_seconds)}</strong> to read aloud.
              </>
            ) : (
              <>Nothing here yet. Type, paste, or drop in a text file.</>
            )}
          </p>
          <input
            ref={fileRef}
            type="file"
            accept=".txt,.md,.markdown,text/plain"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) void readFile(f)
              e.target.value = ''
            }}
          />
          <Button variant="secondary" onClick={() => fileRef.current?.click()}>
            Open a text file
          </Button>
        </div>
      </div>

      {analysis.error && <Banner tone="error" title="Could not read the script">{analysis.error}</Banner>}

      {a?.language_hint === 'hi' && (
        <Banner tone="info" title="Your script is in Hindi">
          Choose a voice that speaks Hindi next. On the captions step, pick Noto Sans Devanagari so every letter shows.
        </Banner>
      )}

      {a && a.warnings.length > 0 && (
        <div className="stack" aria-label="Things to check in your script">
          {a.warnings.map((w) => (
            <Banner key={`${w.code}-${w.sentence_idx ?? ''}`} tone="warn">
              {w.message}
            </Banner>
          ))}
        </div>
      )}

      {a && a.sentences.length > 1 && (
        <details className="disclosure">
          <summary className="disclosure__summary">
            <span>See how long each sentence takes</span>
          </summary>
          <ol className="sentence-list">
            {a.sentences.map((s) => (
              <li key={s.idx} className="sentence">
                <span className="sentence__text">{s.text}</span>
                <span className="sentence__bar" aria-hidden="true">
                  <span
                    className={`sentence__fill ${s.words > LONG_SENTENCE ? 'sentence__fill--long' : ''}`}
                    style={{ width: `${Math.max(4, (s.seconds / longest) * 100)}%` }}
                  />
                </span>
                <span className="sentence__time">
                  {s.seconds.toFixed(1)} s{s.words > LONG_SENTENCE ? ', long' : ''}
                </span>
              </li>
            ))}
          </ol>
        </details>
      )}

      <LengthSection />
    </div>
  )
}
