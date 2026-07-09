import './Lessons.css'

function LessonComplete({ summary, onBackToDashboard }) {
  const activatedCount = summary?.activated_item_ids?.length ?? 0

  return (
    <main className="lesson-screen">
      <h1>Lesson complete!</h1>
      <p>
        {activatedCount} item{activatedCount === 1 ? '' : 's'} activated into Apprentice 1.
      </p>
      <button type="button" className="primary-button" onClick={onBackToDashboard}>
        Back to Dashboard
      </button>
    </main>
  )
}

export default LessonComplete
