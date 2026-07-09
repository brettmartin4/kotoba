import { useState } from 'react'
import Dashboard from './pages/Dashboard'
import Lesson from './pages/Lesson'
import LessonComplete from './pages/LessonComplete'
import LessonQuiz from './pages/LessonQuiz'
import LessonsAvailable from './pages/LessonsAvailable'
import './App.css'

function App() {
  const [view, setView] = useState('dashboard')
  const [lessonSession, setLessonSession] = useState(null)
  const [completionSummary, setCompletionSummary] = useState(null)

  function goToDashboard() {
    setView('dashboard')
    setLessonSession(null)
    setCompletionSummary(null)
  }

  function handleLessonStarted(session) {
    setLessonSession(session)
    setView('lesson')
  }

  function handleQuizComplete(summary) {
    setCompletionSummary(summary)
    setView('complete')
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
    default:
      return <Dashboard onStartLessons={() => setView('lessons-available')} />
  }
}

export default App
