import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchPendingDuplicates, keepDuplicateSeparate, mergeDuplicate, skipDuplicate } from '../api/importActions'
import './Admin.css'

function DuplicateCard({ duplicate, onResolved }) {
  const candidates = duplicate.candidates
  const [selectedTarget, setSelectedTarget] = useState(candidates.length === 1 ? candidates[0].item_id : null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function run(action) {
    setBusy(true)
    setError(null)
    try {
      await action()
      onResolved()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const raw = duplicate.raw_data

  return (
    <div className="queue-card">
      <p className="queue-card-source">
        From <strong>{duplicate.source_display_name}</strong>, row {duplicate.row_number}
      </p>
      <p>{duplicate.message}</p>

      <div className="side-by-side">
        <div className="side-panel">
          <h3>Existing candidate(s)</h3>
          {candidates.map((candidate) => (
            <label key={candidate.item_id} className="candidate-option">
              {candidates.length > 1 && (
                <input
                  type="radio"
                  name={`target-${duplicate.id}`}
                  checked={selectedTarget === candidate.item_id}
                  onChange={() => setSelectedTarget(candidate.item_id)}
                />
              )}
              <Link to={`/items/${candidate.item_id}`}>{candidate.japanese}</Link> ({candidate.kana})
              <div>Meanings: {candidate.meanings.map((m) => m.meaning).join('; ')}</div>
              <div>SRS: {candidate.srs.stage_label}</div>
              <div>Sources: {candidate.sources.map((s) => s.display_name).join(', ') || 'none yet'}</div>
            </label>
          ))}
        </div>

        <div className="side-panel">
          <h3>Imported row</h3>
          <div>
            {raw.japanese} ({raw.kana})
          </div>
          <div>Meanings: {raw.meanings.join('; ')}</div>
          <div>Examples: {raw.examples.length}</div>
          <div>Similar: {raw.similar_items.join('; ') || 'none'}</div>
        </div>
      </div>

      {error && <p className="dashboard-error">{error}</p>}

      <div className="queue-actions">
        <button
          type="button"
          className="primary-button"
          disabled={busy || !selectedTarget}
          onClick={() => run(() => mergeDuplicate(duplicate.id, selectedTarget))}
        >
          Merge into selected
        </button>
        <button type="button" disabled={busy} onClick={() => run(() => keepDuplicateSeparate(duplicate.id))}>
          Keep Separate
        </button>
        <button type="button" disabled={busy} onClick={() => run(() => skipDuplicate(duplicate.id))}>
          Skip
        </button>
      </div>
    </div>
  )
}

function DuplicateQueue() {
  const [duplicates, setDuplicates] = useState(null)
  const [error, setError] = useState(null)

  function load() {
    fetchPendingDuplicates()
      .then(setDuplicates)
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <main className="admin-screen">
      <h1>Duplicate Merge Queue</h1>
      <p>
        <Link to="/admin">&larr; Back to admin</Link>
      </p>

      {error && <p className="dashboard-error">{error}</p>}
      {!duplicates && !error && <p>Loading...</p>}
      {duplicates && duplicates.length === 0 && <p>No duplicates pending review.</p>}

      {duplicates && duplicates.map((duplicate) => <DuplicateCard key={duplicate.id} duplicate={duplicate} onResolved={load} />)}
    </main>
  )
}

export default DuplicateQueue
