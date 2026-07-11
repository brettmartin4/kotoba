import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchPendingChanges, fetchPendingDuplicates } from '../api/importActions'
import { triggerImportRefresh } from '../api/imports'
import { fetchSources, renameSource } from '../api/sources'
import './Admin.css'

function Admin() {
  const [sources, setSources] = useState([])
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshSummary, setRefreshSummary] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [editValue, setEditValue] = useState('')
  const [pendingDuplicateCount, setPendingDuplicateCount] = useState(null)
  const [pendingChangeCount, setPendingChangeCount] = useState(null)

  function load() {
    fetchSources()
      .then(setSources)
      .catch((err) => setError(err.message))
    fetchPendingDuplicates()
      .then((rows) => setPendingDuplicateCount(rows.length))
      .catch(() => {})
    fetchPendingChanges()
      .then((rows) => setPendingChangeCount(rows.length))
      .catch(() => {})
  }

  useEffect(() => {
    load()
  }, [])

  async function handleRefresh() {
    setRefreshing(true)
    setError(null)
    setRefreshSummary(null)
    try {
      const result = await triggerImportRefresh()
      setRefreshSummary(result.summary)
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setRefreshing(false)
    }
  }

  function startEditing(source) {
    setEditingId(source.id)
    setEditValue(source.display_name)
  }

  async function handleRename(sourceId) {
    if (!editValue.trim()) return
    try {
      await renameSource(sourceId, editValue.trim())
      setEditingId(null)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <main className="admin-screen">
      <h1>Admin</h1>

      <section>
        <button type="button" className="primary-button" onClick={handleRefresh} disabled={refreshing}>
          {refreshing ? 'Refreshing...' : 'Refresh Word Banks'}
        </button>
        {refreshSummary && (
          <p>
            {Object.entries(refreshSummary)
              .map(([status, count]) => `${count} ${status}`)
              .join(', ') || 'No files found.'}
          </p>
        )}
        <p>
          <Link to="/admin/import-runs">View import log &rarr;</Link>
        </p>
      </section>

      <section>
        <h2>Pending Review</h2>
        <p>
          <Link to="/admin/duplicates">Duplicate merge queue</Link>
          {pendingDuplicateCount !== null && ` (${pendingDuplicateCount})`}
        </p>
        <p>
          <Link to="/admin/changes">Changed item approval queue</Link>
          {pendingChangeCount !== null && ` (${pendingChangeCount})`}
        </p>
      </section>

      {error && <p className="dashboard-error">{error}</p>}

      <section>
        <h2>Sources</h2>
        <ul className="admin-source-list">
          {sources.map((source) => (
            <li key={source.id}>
              {editingId === source.id ? (
                <>
                  <input value={editValue} onChange={(e) => setEditValue(e.target.value)} />
                  <button type="button" onClick={() => handleRename(source.id)}>
                    Save
                  </button>
                  <button type="button" onClick={() => setEditingId(null)}>
                    Cancel
                  </button>
                </>
              ) : (
                <>
                  <strong>{source.display_name}</strong> ({source.source_key})
                  <button type="button" className="link-button" onClick={() => startEditing(source)}>
                    rename
                  </button>
                </>
              )}
            </li>
          ))}
          {sources.length === 0 && <li>No sources imported yet.</li>}
        </ul>
      </section>
    </main>
  )
}

export default Admin
