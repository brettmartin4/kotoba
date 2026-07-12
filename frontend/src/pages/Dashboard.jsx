import { useEffect, useState } from 'react'
import { fetchDashboard } from '../api/dashboard'
import DashboardActionCard from '../components/DashboardActionCard'
import ItemSpreadPanel from '../components/ItemSpreadPanel'
import LevelProgressPanel from '../components/LevelProgressPanel'
import ReviewForecast from '../components/ReviewForecast'
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
        <img src="/logo.png" alt="KotobaForge" className="dashboard-logo" />
        <p className="dashboard-error">Could not load dashboard: {error}</p>
      </main>
    )
  }

  if (!data) {
    return (
      <main className="dashboard">
        <img src="/logo.png" alt="KotobaForge" className="dashboard-logo" />
        <p>Loading...</p>
      </main>
    )
  }

  return (
    <main className="dashboard">
      <img src="/logo.png" alt="KotobaForge" className="dashboard-logo" />

      <div className="dashboard-actions">
        <DashboardActionCard
          variant="lessons"
          glyph="授業"
          title="Lessons"
          count={data.lessons_available}
          buttonLabel="Start Lessons"
          onClick={onStartLessons}
          disabled={data.lessons_available === 0}
        />
        <DashboardActionCard
          variant="reviews"
          glyph="練習"
          title="Reviews"
          count={data.reviews_available}
          buttonLabel={startingReview ? 'Starting...' : 'Start Reviews'}
          onClick={onStartReviews}
          disabled={data.reviews_available === 0 || startingReview}
        />
        <ReviewForecast forecast={data.review_forecast} />
      </div>
      {reviewStartError && <p className="dashboard-error">{reviewStartError}</p>}

      <section>
        <h2>Level Progress</h2>
        {data.sources.length === 0 ? (
          <p>No word banks imported yet.</p>
        ) : (
          <div className="level-progress-stack">
            {data.sources.map((source) => (
              <LevelProgressPanel key={source.id} source={source} />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2>Item Spread</h2>
        <ItemSpreadPanel distributionByType={data.srs_distribution_by_type} />
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
