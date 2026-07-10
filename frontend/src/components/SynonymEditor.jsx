import { useState } from 'react'
import { addSynonym, deleteSynonym } from '../api/items'

function SynonymEditor({ itemId, meanings, onChange }) {
  const [newSynonym, setNewSynonym] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleAdd(e) {
    e.preventDefault()
    if (!newSynonym.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      await addSynonym(itemId, newSynonym.trim())
      setNewSynonym('')
      onChange()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(meaningId) {
    setError(null)
    try {
      await deleteSynonym(itemId, meaningId)
      onChange()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="synonym-editor">
      <ul className="meaning-list">
        {meanings.map((m) => (
          <li key={m.id}>
            {m.meaning}
            {m.origin === 'user_synonym' ? (
              <button type="button" className="link-button" onClick={() => handleDelete(m.id)}>
                remove
              </button>
            ) : (
              <span className="meaning-origin"> (imported)</span>
            )}
          </li>
        ))}
      </ul>
      <form onSubmit={handleAdd}>
        <input
          type="text"
          placeholder="Add a synonym"
          value={newSynonym}
          onChange={(e) => setNewSynonym(e.target.value)}
          disabled={submitting}
        />
        <button type="submit" disabled={submitting || !newSynonym.trim()}>
          Add
        </button>
      </form>
      {error && <p className="dashboard-error">{error}</p>}
    </div>
  )
}

export default SynonymEditor
