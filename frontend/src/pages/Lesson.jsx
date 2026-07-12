import { useState } from 'react'
import StudyBanner from '../components/StudyBanner'
import './Lessons.css'
import './StudyScreen.css'

function Lesson({ session, onDone }) {
  const [index, setIndex] = useState(0)
  const item = session.items[index]
  const isLast = index === session.items.length - 1
  const typeLabel = item.item_type === 'word' ? 'Word' : 'Phrase'

  function handleContinue() {
    if (isLast) {
      onDone()
    } else {
      setIndex(index + 1)
    }
  }

  return (
    <main className="study-screen">
      <StudyBanner
        itemType={item.item_type}
        display={item.japanese}
        label={`${typeLabel} · Item ${index + 1} of ${session.items.length}`}
      />

      <div className="study-content">
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

        <button type="button" key={index} className="primary-button" onClick={handleContinue} autoFocus>
          {isLast ? 'Start Quiz' : 'Continue'}
        </button>
      </div>
    </main>
  )
}

export default Lesson
