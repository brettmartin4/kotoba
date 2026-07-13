import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchPendingChanges, fetchPendingDuplicates } from '../api/importActions'
import { triggerImportRefresh } from '../api/imports'
import { fetchSettings, updateDailyLessonCap } from '../api/settings'
import { fetchSources, renameSource } from '../api/sources'
import './Admin.css'

function Admin() {
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshSummary, setRefreshSummary] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [editValue, setEditValue] = useState('')
  const [pendingDuplicateCount, setPendingDuplicateCount] = useState(null)
  const [pendingChangeCount, setPendingChangeCount] = useState(null)
  const [capInput, setCapInput] = useState('')
  const [savingCap, setSavingCap] = useState(false)
  const [capSaved, setCapSaved] = useState(false)

  function load() {
    fetchSources()
      .then(setSources)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
    fetchPendingDuplicates()
      .then((rows) => setPendingDuplicateCount(rows.length))
      .catch(() => {})
    fetchPendingChanges()
      .then((rows) => setPendingChangeCount(rows.length))
      .catch(() => {})
    fetchSettings()
      .then((s) => setCapInput(String(s.daily_lesson_cap)))
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

  async function handleSaveCap(e) {
    e.preventDefault()
    const value = parseInt(capInput, 10)
    if (!Number.isInteger(value) || value < 1) {
      setError('Daily lesson cap must be a whole number of at least 1.')
      return
    }
    setSavingCap(true)
    setCapSaved(false)
    setError(null)
    try {
      const result = await updateDailyLessonCap(value)
      setCapInput(String(result.daily_lesson_cap))
      setCapSaved(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingCap(false)
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

      <section>
        <h2>Settings</h2>
        <form className="settings-form" onSubmit={handleSaveCap}>
          <label htmlFor="daily-lesson-cap">Daily lesson cap</label>
          <input
            id="daily-lesson-cap"
            type="number"
            min="1"
            step="1"
            value={capInput}
            onChange={(e) => {
              setCapInput(e.target.value)
              setCapSaved(false)
            }}
            disabled={savingCap}
          />
          <button type="submit" className="primary-button" disabled={savingCap || capInput === ''}>
            {savingCap ? 'Saving...' : 'Save'}
          </button>
          {capSaved && <span className="saved-indicator">Saved</span>}
        </form>
        <p className="settings-hint">Maximum new items you can start learning per day, resets at local midnight.</p>
      </section>

      {error && <p className="dashboard-error">{error}</p>}

      <section>
        <h2>Sources</h2>
        {loading ? (
          <p>Loading...</p>
        ) : (
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
        )}
      </section>
    </main>
  )
}

export default Admin
