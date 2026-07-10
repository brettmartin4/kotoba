import { useState } from 'react'
import { completeReview, submitReviewAnswer } from '../api/reviews'
import ItemInfoPanel from '../components/ItemInfoPanel'
import './Lessons.css'
import './Reviews.css'

function buildQueue(items) {
  const queue = []
  for (const item of items) {
    queue.push({ itemId: item.item_id, promptType: 'meaning', item })
    queue.push({ itemId: item.item_id, promptType: 'japanese', item })
  }
  for (let i = queue.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[queue[i], queue[j]] = [queue[j], queue[i]]
  }
  // Separate same-item prompts so they don't land back-to-back (spec 11.3).
  for (let i = 1; i < queue.length; i++) {
    if (queue[i].itemId === queue[i - 1].itemId) {
      for (let j = i + 1; j < queue.length; j++) {
        if (queue[j].itemId !== queue[i].itemId) {
          ;[queue[i], queue[j]] = [queue[j], queue[i]]
          break
        }
      }
    }
  }
  return queue
}

function ReviewSession({ session, onComplete }) {
  const [queue, setQueue] = useState(() => buildQueue(session.items))
  const [answer, setAnswer] = useState('')
  const [feedback, setFeedback] = useState(null) // only set for resolved (correct/incorrect) outcomes
  const [typoMessage, setTypoMessage] = useState(false)
  const [shake, setShake] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [finishing, setFinishing] = useState(false)
  const [error, setError] = useState(null)

  // While showing feedback, keep referring to the prompt just answered rather
  // than the new queue head, so the feedback/info panel match what's on screen.
  const current = feedback ? feedback.prompt : queue[0]

  async function handleSubmit(e) {
    e.preventDefault()
    if (!queue.length || submitting) return
    const prompt = queue[0]
    setSubmitting(true)
    setError(null)
    setTypoMessage(false)
    try {
      const result = await submitReviewAnswer(session.session_id, prompt.itemId, prompt.promptType, answer)
      if (result.status === 'typo_warning') {
        // Not resolved: same prompt stays at the front of the queue, no info
        // panel, no correct answer shown -- just a shake and a retry.
        setTypoMessage(true)
        setShake(true)
        setTimeout(() => setShake(false), 400)
        setAnswer('')
      } else {
        setFeedback({ prompt, status: result.status, correctAnswers: result.correct_answers })
        setQueue((prevQueue) => prevQueue.slice(1))
        setAnswer('')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleContinue() {
    const wasLastPrompt = queue.length === 0
    setFeedback(null)
    if (wasLastPrompt) {
      setFinishing(true)
      try {
        const summary = await completeReview(session.session_id)
        onComplete(summary)
      } catch (err) {
        setError(err.message)
        setFinishing(false)
      }
    }
  }

  if (!current) {
    return (
      <main className="lesson-screen">
        <p>Finishing up...</p>
      </main>
    )
  }

  const promptLabel = current.promptType === 'meaning' ? 'What does this mean?' : 'How do you write this in Japanese?'
  const promptText = current.promptType === 'meaning' ? current.item.japanese : current.item.meanings.join(' / ')
  const remaining = queue.length + (feedback ? 1 : 0)

  return (
    <main className="lesson-screen">
      <p className="lesson-progress">
        {remaining} prompt{remaining === 1 ? '' : 's'} remaining
      </p>

      {error && <p className="dashboard-error">{error}</p>}

      <div className={`quiz-card ${shake ? 'shake' : ''}`}>
        <p className="quiz-label">{promptLabel}</p>
        <h1>{promptText}</h1>

        {!feedback ? (
          <>
            <form onSubmit={handleSubmit}>
              <input
                type="text"
                value={answer}
                onChange={(e) => {
                  setAnswer(e.target.value)
                  setTypoMessage(false)
                }}
                autoFocus
                disabled={submitting}
              />
              <button type="submit" disabled={submitting || !answer.trim()}>
                Submit
              </button>
            </form>
            {typoMessage && <p className="typo-warning">Close, but not quite. Try again.</p>}
          </>
        ) : (
          <div
            className={`quiz-feedback ${feedback.status === 'correct' ? 'quiz-feedback-correct' : 'quiz-feedback-incorrect'}`}
          >
            <p>{feedback.status === 'correct' ? 'Correct!' : 'Incorrect.'}</p>
            {feedback.status === 'incorrect' && <p>Accepted: {feedback.correctAnswers.join(', ')}</p>}
            <button type="button" className="primary-button" onClick={handleContinue} disabled={finishing} autoFocus>
              {finishing ? 'Finishing...' : 'Continue'}
            </button>
          </div>
        )}
      </div>

      {feedback && <ItemInfoPanel item={feedback.prompt.item} />}
    </main>
  )
}

export default ReviewSession
