import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { DurationOption } from '../api/types'
import { Badge, Banner, Button, QualityBadge } from '../components/ui'
import { QUICK_TARGETS, formatDuration } from '../lib/time'
import { useDraft } from '../state/project'
import type { DurationOptionKind } from '../state/project'
import { useScriptInfo } from '../state/scriptInfo'

/** Plain-language name for each way of hitting the target. */
function optionTitle(o: DurationOption): string {
  const faster = (o.speed ?? 1) >= 1
  if (o.kind === 'edit_script') return 'Change the script yourself'
  if (o.kind === 'adjust_delivery') return faster ? 'Speak faster, with shorter pauses' : 'Speak slower, with longer pauses'
  return faster ? 'Speak faster, keep the pauses' : 'Speak slower, keep the pauses'
}

/** "How long should it be?": pick a length, and see how NarraReel will get there. */
export function LengthSection() {
  const { targetSeconds, targetText, durationOption, patch } = useDraft()
  const { plan, analysis } = useScriptInfo()
  const [custom, setCustom] = useState(targetText)
  const [customOpen, setCustomOpen] = useState(false)
  const [customError, setCustomError] = useState<string | null>(null)
  const a = analysis.data
  // while a new plan loads, the previous one belongs to a different target: do not show it
  const planData = plan.data?.plan
  const p = planData && (planData.target_seconds ?? null) === (targetSeconds ?? null) ? planData : undefined
  const isQuick = targetSeconds === null || QUICK_TARGETS.some((t) => t.seconds === targetSeconds)

  useEffect(() => {
    setCustom(targetText)
  }, [targetText])

  const setTarget = (seconds: number | null, text = '') =>
    patch({ targetSeconds: seconds, targetText: text, durationOption: null, ...(seconds ? { speed: 1 } : {}) })

  const applyCustom = async () => {
    if (!custom.trim()) return setTarget(null)
    try {
      const r = await api.parseDuration(custom)
      setCustomError(null)
      setTarget(r.seconds, custom)
    } catch (e) {
      setCustomError(e instanceof Error ? e.message : 'That is not a length NarraReel understands.')
    }
  }

  const natural = a && a.word_count > 0 ? a.estimate.total_seconds : null
  const diff = natural !== null && targetSeconds ? targetSeconds - natural : null
  // the server falls back to adjusting the delivery, so that is what an untouched choice shows
  const selected: DurationOptionKind = durationOption ?? 'adjust_delivery'
  const editOption = p?.options.find((o) => o.kind === 'edit_script')

  return (
    <section className="section" aria-labelledby="length-title">
      <div className="section__head">
        <h2 className="section__title" id="length-title">
          How long should it be?
        </h2>
        <p className="section__hint">
          {natural !== null
            ? `Read at a natural pace, your script takes about ${formatDuration(natural)}.`
            : 'Write your script first and NarraReel will tell you how long it takes to say.'}
        </p>
      </div>

      <div className="choice-row" role="radiogroup" aria-label="Video length">
        <button
          type="button"
          role="radio"
          aria-checked={targetSeconds === null}
          className="choice"
          onClick={() => {
            setCustomOpen(false)
            setTarget(null)
          }}
        >
          Natural length
        </button>
        {QUICK_TARGETS.map((t) => (
          <button
            key={t.seconds}
            type="button"
            role="radio"
            aria-checked={targetSeconds === t.seconds}
            className="choice"
            onClick={() => {
              setCustomOpen(false)
              setTarget(t.seconds, t.label.replace(' ', ''))
            }}
          >
            {t.label}
          </button>
        ))}
        <button
          type="button"
          role="radio"
          aria-checked={customOpen || !isQuick}
          className="choice"
          onClick={() => setCustomOpen(true)}
        >
          {!isQuick && targetSeconds ? formatDuration(targetSeconds) : 'Other'}
        </button>
      </div>

      {(customOpen || !isQuick) && (
        <form
          className="inline-form"
          onSubmit={(e) => {
            e.preventDefault()
            void applyCustom()
          }}
        >
          <div className="field field--grow">
            <label className="field__label" htmlFor="custom-target">
              Exact length
            </label>
            <input
              id="custom-target"
              className="input"
              value={custom}
              placeholder="For example 45s, 1:30 or 2m"
              onChange={(e) => setCustom(e.target.value)}
              aria-invalid={!!customError}
              aria-describedby={customError ? 'custom-error' : undefined}
            />
          </div>
          <Button variant="secondary" type="submit">
            Set length
          </Button>
        </form>
      )}
      {customError && (
        <p id="custom-error" className="field__error">
          {customError}
        </p>
      )}

      {plan.error && targetSeconds && <Banner tone="error" title="Could not work out the length">{plan.error}</Banner>}

      {p && targetSeconds && diff !== null && (
        <div className="fit">
          <p className="fit__lead">
            {Math.abs(diff) < 1 ? (
              <>Your script already fits {formatDuration(targetSeconds)}.</>
            ) : (
              <>
                Your script is <strong>{formatDuration(Math.abs(diff))} {diff < 0 ? 'too long' : 'too short'}</strong> for{' '}
                {formatDuration(targetSeconds)}. Choose how to fix it:
              </>
            )}
          </p>
          {Math.abs(diff) >= 1 && (
            <div className="fit__options" role="radiogroup" aria-label="How to fit the length">
              {p.options.map((o, i) => {
                const on = o.kind === selected
                return (
                  <button
                    key={o.kind}
                    type="button"
                    role="radio"
                    aria-checked={on}
                    className="fit-option"
                    onClick={() => patch({ durationOption: o.kind as DurationOptionKind })}
                  >
                    <span className="fit-option__radio" aria-hidden="true" />
                    <span className="fit-option__body">
                      <span className="fit-option__title">
                        {optionTitle(o)}
                        {i === p.recommended && <Badge tone="yellow">Recommended</Badge>}
                      </span>
                      <span className="fit-option__text">
                        {o.kind === 'edit_script'
                          ? o.message
                          : `${Math.abs(o.resulting_seconds - targetSeconds) < 0.5 ? 'Ends at exactly' : 'Gets as close as it can:'} ${formatDuration(o.resulting_seconds)}. Speed ${(o.speed ?? 1).toFixed(2)}×.`}
                      </span>
                    </span>
                    {o.kind !== 'edit_script' && <QualityBadge quality={o.quality} />}
                  </button>
                )
              })}
            </div>
          )}
          {selected === 'edit_script' && editOption && (
            <p className="fit__live" aria-live="polite">
              {Math.abs(editOption.words_delta ?? 0) < 2
                ? 'Your script now fits at a natural pace.'
                : editOption.message}{' '}
              This updates as you edit the script above.
            </p>
          )}
        </div>
      )}
    </section>
  )
}
