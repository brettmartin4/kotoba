import { useState } from 'react'
import './Lessons.css'

function Lesson({ session, onDone }) {
  const [index, setIndex] = useState(0)
  const item = session.items[index]
  const isLast = index === session.items.length - 1

  function handleContinue() {
    if (isLast) {
      onDone()
    } else {
      setIndex(index + 1)
    }
  }

  return (
    <main className="lesson-screen">
      <p className="lesson-progress">
        Item {index + 1} of {session.items.length}
      </p>
      <div className="lesson-card">
        <h1>{item.japanese}</h1>
        <p className="lesson-kana">
          {item.kana} &middot; {item.romaji}
        </p>
        <p>{item.part_of_speech}</p>
        <p>{item.meanings.join('; ')}</p>

        {item.examples.length > 0 && (
          <div className="lesson-examples">
            <h3>Examples</h3>
            {item.examples.map((example, i) => (
              <div key={i} className="lesson-example">
                <p>{example.japanese_sentence}</p>
                <p className="lesson-kana">{example.kana_sentence}</p>
                <p>{example.english_translation}</p>
              </div>
            ))}
          </div>
        )}

        {item.similar_items.length > 0 && <p>Similar: {item.similar_items.join('; ')}</p>}

        {(item.notes.note_text || item.notes.mnemonic_text) && (
          <div className="lesson-notes">
            {item.notes.note_text && <p>Note: {item.notes.note_text}</p>}
            {item.notes.mnemonic_text && <p>Mnemonic: {item.notes.mnemonic_text}</p>}
          </div>
        )}
      </div>

      <button type="button" className="primary-button" onClick={handleContinue}>
        {isLast ? 'Start Quiz' : 'Continue'}
      </button>
    </main>
  )
}

export default Lesson
