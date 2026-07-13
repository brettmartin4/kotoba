import { useCallback, useRef } from 'react'
import * as wanakana from 'wanakana'
import { ChevronIcon } from './icons'

// The input and the result feedback are the same element (WK-style): plain
// while typing, then it turns green/red in place once resolved, with the
// chevron doubling as submit (while typing) and continue (once resolved).
function AnswerBar({
  value,
  onChange,
  onSubmit,
  submitting,
  shake,
  typoMessage,
  result, // null | 'correct' | 'incorrect'
  submittedAnswer,
  correctAnswers,
  onContinue,
  continuing,
  convertToKana, // true for Japanese-production prompts: romaji is converted to
  // hiragana live as you type (wanakana), so you never have to touch your OS
  // IME toggle. This is a real DOM binding, not a controlled-value transform,
  // so it must be re-attached every time a fresh <input> mounts -- the input
  // fully unmounts/remounts between every prompt (see the `result` branch
  // above), so a plain useEffect keyed on `convertToKana` alone would miss
  // rebinding on the next prompt if the direction happens to stay the same.
  // A stable (useCallback) ref callback is called by React on every mount of
  // a NEW dom node regardless of whether its own identity changed, which is
  // exactly the semantics needed here.
}) {
  const boundNodeRef = useRef(null)

  const setInputRef = useCallback(
    (node) => {
      if (boundNodeRef.current) {
        wanakana.unbind(boundNodeRef.current)
        boundNodeRef.current = null
      }
      if (node && convertToKana) {
        wanakana.bind(node, { IMEMode: 'toHiragana' })
        boundNodeRef.current = node
      }
    },
    [convertToKana],
  )

  if (result) {
    return (
      <div className={`answer-bar full-bleed answer-bar-${result}`}>
        <span className="answer-bar-text">
          {result === 'correct' ? submittedAnswer : correctAnswers.join(', ')}
        </span>
        <button
          type="button"
          className="answer-bar-chevron"
          onClick={onContinue}
          disabled={continuing}
          autoFocus
          aria-label="Continue"
        >
          <ChevronIcon />
        </button>
      </div>
    )
  }

  return (
    <div className={`answer-bar-wrap ${shake ? 'shake' : ''}`}>
      <form className="answer-bar full-bleed" onSubmit={onSubmit} autoComplete="off">
        <input
          ref={setInputRef}
          type="text"
          className="answer-bar-input"
          value={value}
          onChange={onChange}
          placeholder="Answer"
          autoFocus
          disabled={submitting}
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck="false"
        />
        <button
          type="submit"
          className="answer-bar-chevron"
          disabled={submitting || !value.trim()}
          aria-label="Submit"
        >
          <ChevronIcon />
        </button>
      </form>
      {typoMessage && <p className="typo-warning">Close, but not quite. Try again.</p>}
    </div>
  )
}

export default AnswerBar
