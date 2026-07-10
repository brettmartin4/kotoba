import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchImportRunDetail } from '../api/imports'
import './Admin.css'

function ImportRunDetail() {
  const { runId } = useParams()
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchImportRunDetail(runId)
      .then(setDetail)
      .catch((err) => setError(err.message))
  }, [runId])

  if (error) {
    return (
      <main className="admin-screen">
        <p className="dashboard-error">{error}</p>
      </main>
    )
  }

  if (!detail) {
    return (
      <main className="admin-screen">
        <p>Loading...</p>
      </main>
    )
  }

  return (
    <main className="admin-screen">
      <h1>Import Run #{detail.run.id}</h1>
      <p>
        <Link to="/admin/import-runs">&larr; Back to import log</Link>
      </p>
      <p>Status: {detail.run.status}</p>

      <table className="browse-table">
        <thead>
          <tr>
            <th>Row</th>
            <th>Status</th>
            <th>Japanese</th>
            <th>Message</th>
            <th>Candidates</th>
          </tr>
        </thead>
        <tbody>
          {detail.items.map((item) => (
            <tr key={item.id}>
              <td>{item.row_number ?? '—'}</td>
              <td>{item.status}</td>
              <td>
                {item.raw_data?.japanese ??
                  (item.item_id ? <Link to={`/items/${item.item_id}`}>view item</Link> : '—')}
              </td>
              <td>{item.message}</td>
              <td>
                {item.candidate_item_ids && item.candidate_item_ids.length > 0
                  ? item.candidate_item_ids.map((candidateId) => (
                      <Link key={candidateId} to={`/items/${candidateId}`}>
                        #{candidateId}{' '}
                      </Link>
                    ))
                  : '—'}
              </td>
            </tr>
          ))}
          {detail.items.length === 0 && (
            <tr>
              <td colSpan={5}>No rows recorded for this run.</td>
            </tr>
          )}
        </tbody>
      </table>
    </main>
  )
}

export default ImportRunDetail
