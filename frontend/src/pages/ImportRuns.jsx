import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchImportRuns } from '../api/imports'
import './Admin.css'

function ImportRuns() {
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchImportRuns()
      .then(setRuns)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <main className="admin-screen">
      <h1>Import Log</h1>
      <p>
        <Link to="/admin">&larr; Back to admin</Link>
      </p>

      {error && <p className="dashboard-error">{error}</p>}

      {loading ? (
        <p>Loading...</p>
      ) : (
        <table className="browse-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Started</th>
              <th>Status</th>
              <th>Summary</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td>
                  <Link to={`/admin/import-runs/${run.id}`}>#{run.id}</Link>
                </td>
                <td>{run.started_at}</td>
                <td>{run.status}</td>
                <td>{run.summary_json}</td>
              </tr>
            ))}
            {runs.length === 0 && (
              <tr>
                <td colSpan={4}>No import runs yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </main>
  )
}

export default ImportRuns
