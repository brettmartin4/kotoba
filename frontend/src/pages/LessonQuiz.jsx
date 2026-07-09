import { useState } from 'react'
import { completeLesson, submitLessonAnswer } from '../api/lessons'
import './Lessons.css'

function buildInitialQueue(items) {
  const queue = []
  for (const item of items) {
    queue.push({ itemId: item.item_id, promptType: 'meaning', item })
    queue.push({ itemId: item.item_id, promptType: 'japanese', item })
  }
  for (let i = queue.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[queue[i], queue[j]] = [queue[j], queue[i]]
  }
  return queue
}

function LessonQuiz({ session, onComplete }) {
  const [queue, setQueue] = useState(() => buildInitialQueue(session.items))
  const [answer, setAnswer] = useState('')
  const [feedback, setFeedback] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [finishing, setFinishing] = useState(false)
  const [error, setError] = useState(null)

  // While showing feedback, keep referring to the prompt just answered rather
  // than the new queue head, so the feedback text matches what's on screen.
  const current = feedback ? feedback.prompt : queue[0]

  async function handleSubmit(e) {
    e.preventDefault()
    if (!queue.length || submitting) return
    const prompt = queue[0]
    setSubmitting(true)
    setError(null)
    try {
      const result = await submitLessonAnswer(session.session_id, prompt.itemId, prompt.promptType, answer)
      setFeedback({ prompt, isCorrect: result.is_correct, correctAnswers: result.correct_answers })
      setQueue((prevQueue) => {
        const rest = prevQueue.slice(1)
        return result.is_correct ? rest : [...rest, prompt]
      })
      setAnswer('')
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
        const summary = await completeLesson(session.session_id)
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

      <div className="quiz-card">
        <p className="quiz-label">{promptLabel}</p>
        <h1>{promptText}</h1>

        {!feedback ? (
          <form onSubmit={handleSubmit}>
            <input
              type="text"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              autoFocus
              disabled={submitting}
            />
            <button type="submit" disabled={submitting || !answer.trim()}>
              Submit
            </button>
          </form>
        ) : (
          <div className={`quiz-feedback ${feedback.isCorrect ? 'quiz-feedback-correct' : 'quiz-feedback-incorrect'}`}>
            <p>{feedback.isCorrect ? 'Correct!' : 'Incorrect.'}</p>
            {!feedback.isCorrect && <p>Accepted: {feedback.correctAnswers.join(', ')}</p>}
            <button type="button" className="primary-button" onClick={handleContinue} disabled={finishing} autoFocus>
              {finishing ? 'Finishing...' : 'Continue'}
            </button>
          </div>
        )}
      </div>
    </main>
  )
}

export default LessonQuiz
