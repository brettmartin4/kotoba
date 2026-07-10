import { useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { startReview } from './api/reviews'
import Layout from './components/Layout'
import Admin from './pages/Admin'
import Browse from './pages/Browse'
import Dashboard from './pages/Dashboard'
import ImportRunDetail from './pages/ImportRunDetail'
import ImportRuns from './pages/ImportRuns'
import ItemDetail from './pages/ItemDetail'
import Lesson from './pages/Lesson'
import LessonComplete from './pages/LessonComplete'
import LessonQuiz from './pages/LessonQuiz'
import LessonsAvailable from './pages/LessonsAvailable'
import ReviewComplete from './pages/ReviewComplete'
import ReviewSession from './pages/ReviewSession'

function AppRoutes() {
  const navigate = useNavigate()
  const [lessonSession, setLessonSession] = useState(null)
  const [completionSummary, setCompletionSummary] = useState(null)
  const [reviewSession, setReviewSession] = useState(null)
  const [reviewCompletionSummary, setReviewCompletionSummary] = useState(null)
  const [reviewStartError, setReviewStartError] = useState(null)
  const [startingReview, setStartingReview] = useState(false)

  function goToDashboard() {
    navigate('/')
    setLessonSession(null)
    setCompletionSummary(null)
    setReviewSession(null)
    setReviewCompletionSummary(null)
    setReviewStartError(null)
  }

  function handleLessonStarted(session) {
    setLessonSession(session)
    navigate('/lessons/session')
  }

  function handleQuizComplete(summary) {
    setCompletionSummary(summary)
    navigate('/lessons/complete')
  }

  async function handleStartReviews() {
    setReviewStartError(null)
    setStartingReview(true)
    try {
      const session = await startReview()
      setReviewSession(session)
      navigate('/reviews/session')
    } catch (err) {
      setReviewStartError(err.message)
    } finally {
      setStartingReview(false)
    }
  }

  function handleReviewComplete(summary) {
    setReviewCompletionSummary(summary)
    navigate('/reviews/complete')
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route
          path="/"
          element={
            <Dashboard
              onStartLessons={() => navigate('/lessons')}
              onStartReviews={handleStartReviews}
              reviewStartError={reviewStartError}
              startingReview={startingReview}
            />
          }
        />
        <Route path="/browse" element={<Browse />} />
        <Route path="/items/:itemId" element={<ItemDetail />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="/admin/import-runs" element={<ImportRuns />} />
        <Route path="/admin/import-runs/:runId" element={<ImportRunDetail />} />
      </Route>

      <Route path="/lessons" element={<LessonsAvailable onBack={goToDashboard} onStart={handleLessonStarted} />} />
      <Route
        path="/lessons/session"
        element={
          lessonSession ? <Lesson session={lessonSession} onDone={() => navigate('/lessons/quiz')} /> : <Navigate to="/lessons" replace />
        }
      />
      <Route
        path="/lessons/quiz"
        element={
          lessonSession ? (
            <LessonQuiz session={lessonSession} onComplete={handleQuizComplete} />
          ) : (
            <Navigate to="/lessons" replace />
          )
        }
      />
      <Route
        path="/lessons/complete"
        element={<LessonComplete summary={completionSummary} onBackToDashboard={goToDashboard} />}
      />

      <Route
        path="/reviews/session"
        element={
          reviewSession ? (
            <ReviewSession session={reviewSession} onComplete={handleReviewComplete} />
          ) : (
            <Navigate to="/" replace />
          )
        }
      />
      <Route
        path="/reviews/complete"
        element={<ReviewComplete summary={reviewCompletionSummary} onBackToDashboard={goToDashboard} />}
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default AppRoutes
