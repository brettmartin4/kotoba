import { useEffect, useState } from 'react'
import { fetchDashboard } from '../api/dashboard'
import SourceLevelCard from '../components/SourceLevelCard'
import SrsDistribution from '../components/SrsDistribution'
import './Dashboard.css'

function Dashboard({ onStartLessons, onStartReviews, reviewStartError, startingReview }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchDashboard()
      .then(setData)
      .catch((err) => setError(err.message))
  }, [])

  if (error) {
    return (
      <main className="dashboard">
        <h1>KotobaForge</h1>
        <p className="dashboard-error">Could not load dashboard: {error}</p>
      </main>
    )
  }

  if (!data) {
    return (
      <main className="dashboard">
        <h1>KotobaForge</h1>
        <p>Loading...</p>
      </main>
    )
  }

  return (
    <main className="dashboard">
      <h1>KotobaForge</h1>

      <div className="dashboard-actions">
        <button
          className="action-button"
          type="button"
          onClick={onStartLessons}
          disabled={data.lessons_available === 0}
        >
          Lessons
          <span className="action-count">{data.lessons_available}</span>
        </button>
        <button
          className="action-button"
          type="button"
          onClick={onStartReviews}
          disabled={data.reviews_available === 0 || startingReview}
        >
          {startingReview ? 'Starting...' : 'Reviews'}
          <span className="action-count">{data.reviews_available}</span>
        </button>
      </div>
      {reviewStartError && <p className="dashboard-error">{reviewStartError}</p>}

      <section>
        <h2>Sources</h2>
        {data.sources.length === 0 ? (
          <p>No word banks imported yet.</p>
        ) : (
          <div className="source-cards">
            {data.sources.map((source) => (
              <SourceLevelCard key={source.id} source={source} />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2>SRS Distribution</h2>
        <SrsDistribution distribution={data.srs_distribution} />
      </section>

      <section className="dashboard-footer">
        <p>
          Daily streak: {data.daily_streak} day{data.daily_streak === 1 ? '' : 's'}
        </p>
        <p>
          {data.new_items_last_7_days} word{data.new_items_last_7_days === 1 ? '' : 's'} added in the last 7 days.
        </p>
        <p>
          Lessons learned today: {data.lessons_learned_today} / {data.daily_lesson_cap}
        </p>
      </section>
    </main>
  )
}

export default Dashboard
