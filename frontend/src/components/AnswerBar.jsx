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
}) {
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
      <form className="answer-bar full-bleed" onSubmit={onSubmit}>
        <input
          type="text"
          className="answer-bar-input"
          value={value}
          onChange={onChange}
          placeholder="Answer"
          autoFocus
          disabled={submitting}
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
