import { useEffect, useState } from 'react'
import { fetchLessonsAvailable, startLesson } from '../api/lessons'
import './Lessons.css'

function LessonsAvailable({ onBack, onStart }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [startingSourceId, setStartingSourceId] = useState(null)

  useEffect(() => {
    fetchLessonsAvailable()
      .then(setData)
      .catch((err) => setError(err.message))
  }, [])

  async function handleStart(sourceId) {
    setError(null)
    setStartingSourceId(sourceId)
    try {
      const session = await startLesson(sourceId)
      onStart(session)
    } catch (err) {
      setError(err.message)
      setStartingSourceId(null)
    }
  }

  return (
    <main className="lessons-screen">
      <h1>Lessons</h1>
      <button type="button" className="back-link" onClick={onBack}>
        &larr; Back to dashboard
      </button>

      {error && <p className="dashboard-error">{error}</p>}
      {!data && !error && <p>Loading...</p>}

      {data && (
        <>
          <p>
            Daily cap: {data.lessons_learned_today} / {data.daily_lesson_cap} learned today (
            {data.remaining_today} remaining)
          </p>
          {data.sources.length === 0 ? (
            <p>No word banks imported yet.</p>
          ) : (
            <div className="source-cards">
              {data.sources.map((source) => (
                <div key={source.source_id} className="source-card">
                  <h3>{source.display_name}</h3>
                  <p>{source.current_level > 0 ? `Level ${source.current_level}` : 'No items yet'}</p>
                  <p>
                    {source.lessons_available_in_source} lesson
                    {source.lessons_available_in_source === 1 ? '' : 's'} available
                  </p>
                  <button
                    type="button"
                    className="primary-button"
                    disabled={
                      source.lessons_available_in_source === 0 ||
                      data.remaining_today === 0 ||
                      startingSourceId === source.source_id
                    }
                    onClick={() => handleStart(source.source_id)}
                  >
                    {startingSourceId === source.source_id ? 'Starting...' : 'Start Lesson'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </main>
  )
}

export default LessonsAvailable
