import './Lessons.css'

function ReviewComplete({ summary, onBackToDashboard }) {
  const results = summary?.results ?? []
  const passedCount = results.filter((r) => r.passed).length

  return (
    <main className="lesson-screen">
      <h1>Reviews complete!</h1>
      <p>
        {passedCount} of {results.length} item{results.length === 1 ? '' : 's'} advanced.
      </p>
      <button type="button" className="primary-button" onClick={onBackToDashboard}>
        Back to Dashboard
      </button>
    </main>
  )
}

export default ReviewComplete
