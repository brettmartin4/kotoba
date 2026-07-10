import { useState } from 'react'
import { startReview } from './api/reviews'
import Dashboard from './pages/Dashboard'
import Lesson from './pages/Lesson'
import LessonComplete from './pages/LessonComplete'
import LessonQuiz from './pages/LessonQuiz'
import LessonsAvailable from './pages/LessonsAvailable'
import ReviewComplete from './pages/ReviewComplete'
import ReviewSession from './pages/ReviewSession'
import './App.css'

function App() {
  const [view, setView] = useState('dashboard')
  const [lessonSession, setLessonSession] = useState(null)
  const [completionSummary, setCompletionSummary] = useState(null)
  const [reviewSession, setReviewSession] = useState(null)
  const [reviewCompletionSummary, setReviewCompletionSummary] = useState(null)
  const [reviewStartError, setReviewStartError] = useState(null)
  const [startingReview, setStartingReview] = useState(false)

  function goToDashboard() {
    setView('dashboard')
    setLessonSession(null)
    setCompletionSummary(null)
    setReviewSession(null)
    setReviewCompletionSummary(null)
    setReviewStartError(null)
  }

  function handleLessonStarted(session) {
    setLessonSession(session)
    setView('lesson')
  }

  function handleQuizComplete(summary) {
    setCompletionSummary(summary)
    setView('complete')
  }

  async function handleStartReviews() {
    setReviewStartError(null)
    setStartingReview(true)
    try {
      const session = await startReview()
      setReviewSession(session)
      setView('review')
    } catch (err) {
      setReviewStartError(err.message)
    } finally {
      setStartingReview(false)
    }
  }

  function handleReviewComplete(summary) {
    setReviewCompletionSummary(summary)
    setView('review-complete')
  }

  switch (view) {
    case 'lessons-available':
      return <LessonsAvailable onBack={goToDashboard} onStart={handleLessonStarted} />
    case 'lesson':
      return <Lesson session={lessonSession} onDone={() => setView('quiz')} />
    case 'quiz':
      return <LessonQuiz session={lessonSession} onComplete={handleQuizComplete} />
    case 'complete':
      return <LessonComplete summary={completionSummary} onBackToDashboard={goToDashboard} />
    case 'review':
      return <ReviewSession session={reviewSession} onComplete={handleReviewComplete} />
    case 'review-complete':
      return <ReviewComplete summary={reviewCompletionSummary} onBackToDashboard={goToDashboard} />
    default:
      return (
        <Dashboard
          onStartLessons={() => setView('lessons-available')}
          onStartReviews={handleStartReviews}
          reviewStartError={reviewStartError}
          startingReview={startingReview}
        />
      )
  }
}

export default App
