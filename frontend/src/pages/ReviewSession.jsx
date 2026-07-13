import { useState } from 'react'
import { completeReview, submitReviewAnswer } from '../api/reviews'
import AnswerBar from '../components/AnswerBar'
import ItemInfoPanel from '../components/ItemInfoPanel'
import StudyBanner from '../components/StudyBanner'
import UtilityRow from '../components/UtilityRow'
import { promptFurigana, promptLabel } from '../utils/studyLabels'
import './Lessons.css'
import './Reviews.css'
import './StudyScreen.css'

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
  const [panelOpen, setPanelOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [finishing, setFinishing] = useState(false)
  const [error, setError] = useState(null)
  const [correctCount, setCorrectCount] = useState(0)
  const [resolvedCount, setResolvedCount] = useState(0)

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
        setFeedback({ prompt, status: result.status, correctAnswers: result.correct_answers, submittedAnswer: answer })
        setQueue((prevQueue) => prevQueue.slice(1))
        setAnswer('')
        setPanelOpen(false)
        setResolvedCount((c) => c + 1)
        if (result.status === 'correct') setCorrectCount((c) => c + 1)
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
    setPanelOpen(false)
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

  const promptText = current.promptType === 'meaning' ? current.item.japanese : current.item.meanings.join(' / ')
  const remaining = queue.length + (feedback ? 1 : 0)
  const accuracy = resolvedCount > 0 ? Math.round((correctCount / resolvedCount) * 100) : null

  return (
    <main className="study-screen">
      <p className="study-topbar">
        {accuracy === null ? 'No answers yet' : `${accuracy}% correct`} &middot; {remaining} remaining
      </p>

      {error && (
        <p className="study-content dashboard-error">
          {error}
        </p>
      )}

      <StudyBanner
        itemType={current.item.item_type}
        display={promptText}
        label={promptLabel(current.item.item_type, current.promptType)}
        furigana={promptFurigana(current.item, current.promptType)}
      />

      <AnswerBar
        value={answer}
        onChange={(e) => {
          setAnswer(e.target.value)
          setTypoMessage(false)
        }}
        onSubmit={handleSubmit}
        submitting={submitting}
        shake={shake}
        typoMessage={typoMessage}
        result={feedback ? feedback.status : null}
        submittedAnswer={feedback ? feedback.submittedAnswer : ''}
        correctAnswers={feedback ? feedback.correctAnswers : []}
        onContinue={handleContinue}
        continuing={finishing}
        convertToKana={current.promptType === 'japanese'}
      />

      <UtilityRow
        itemId={current.item.item_id}
        revealEnabled={!!feedback}
        revealed={panelOpen}
        onToggleReveal={() => setPanelOpen((v) => !v)}
      />

      <div className="study-content">{feedback && panelOpen && <ItemInfoPanel item={feedback.prompt.item} />}</div>
    </main>
  )
}

export default ReviewSession
