import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { approveChange, fetchPendingChanges, rejectChange } from '../api/importActions'
import './Admin.css'

function ChangeCard({ change, onResolved }) {
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

  const raw = change.raw_data
  const current = change.current_item

  return (
    <div className="queue-card">
      <p className="queue-card-source">
        From <strong>{change.source_display_name}</strong>, row {change.row_number} &middot;{' '}
        <Link to={`/items/${current.item_id}`}>{current.japanese}</Link>
      </p>
      <p>{change.message}</p>

      <table className="browse-table">
        <thead>
          <tr>
            <th>Field</th>
            <th>Current</th>
            <th>Imported</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>romaji</td>
            <td>{current.romaji}</td>
            <td>{raw.romaji}</td>
          </tr>
          <tr>
            <td>part of speech</td>
            <td>{current.part_of_speech}</td>
            <td>{raw.part_of_speech}</td>
          </tr>
          <tr>
            <td>meanings</td>
            <td>{current.meanings.map((m) => m.meaning).join('; ')}</td>
            <td>{raw.meanings.join('; ')}</td>
          </tr>
          <tr>
            <td>similar items</td>
            <td>{current.similar_items.join('; ')}</td>
            <td>{raw.similar_items.join('; ')}</td>
          </tr>
        </tbody>
      </table>

      {error && <p className="dashboard-error">{error}</p>}

      <div className="queue-actions">
        <button
          type="button"
          className="primary-button"
          disabled={busy}
          onClick={() => run(() => approveChange(change.id))}
        >
          Approve
        </button>
        <button type="button" disabled={busy} onClick={() => run(() => rejectChange(change.id))}>
          Reject
        </button>
      </div>
    </div>
  )
}

function ChangeQueue() {
  const [changes, setChanges] = useState(null)
  const [error, setError] = useState(null)

  function load() {
    fetchPendingChanges()
      .then(setChanges)
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <main className="admin-screen">
      <h1>Changed Item Approval Queue</h1>
      <p>
        <Link to="/admin">&larr; Back to admin</Link>
      </p>

      {error && <p className="dashboard-error">{error}</p>}
      {!changes && !error && <p>Loading...</p>}
      {changes && changes.length === 0 && <p>No changes pending approval.</p>}

      {changes && changes.map((change) => <ChangeCard key={change.id} change={change} onResolved={load} />)}
    </main>
  )
}

export default ChangeQueue
