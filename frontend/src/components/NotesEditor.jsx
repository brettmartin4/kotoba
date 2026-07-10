import { useEffect, useState } from 'react'
import { updateItemNotes } from '../api/items'

function NotesEditor({ itemId, notes }) {
  const [noteText, setNoteText] = useState(notes.note_text || '')
  const [mnemonicText, setMnemonicText] = useState(notes.mnemonic_text || '')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    setNoteText(notes.note_text || '')
    setMnemonicText(notes.mnemonic_text || '')
  }, [notes])

  async function handleSave() {
    setSaving(true)
    setSaved(false)
    setError(null)
    try {
      await updateItemNotes(itemId, { note_text: noteText, mnemonic_text: mnemonicText })
      setSaved(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="notes-editor">
      <label>
        Note
        <textarea
          value={noteText}
          onChange={(e) => {
            setNoteText(e.target.value)
            setSaved(false)
          }}
          rows={3}
        />
      </label>
      <label>
        Mnemonic
        <textarea
          value={mnemonicText}
          onChange={(e) => {
            setMnemonicText(e.target.value)
            setSaved(false)
          }}
          rows={3}
        />
      </label>
      <div>
        <button type="button" className="primary-button" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save'}
        </button>
        {saved && <span className="saved-indicator">Saved</span>}
      </div>
      {error && <p className="dashboard-error">{error}</p>}
    </div>
  )
}

export default NotesEditor
