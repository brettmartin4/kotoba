import { useState } from 'react'
import '../pages/Reviews.css'

const TABS = ['Meaning', 'Reading', 'Examples', 'Notes', 'Similar']

function ItemInfoPanel({ item }) {
  const [activeTab, setActiveTab] = useState('Meaning')

  return (
    <div className="item-info-panel">
      <div className="info-tabs">
        {TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            className={activeTab === tab ? 'info-tab active' : 'info-tab'}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>
      <div className="info-tab-content">
        {activeTab === 'Meaning' && (
          <div>
            <p>{item.meanings.join('; ')}</p>
            <p>{item.part_of_speech}</p>
          </div>
        )}

        {activeTab === 'Reading' && (
          <div>
            <p>{item.japanese}</p>
            <p>{item.kana}</p>
            <p>{item.romaji}</p>
          </div>
        )}

        {activeTab === 'Examples' &&
          (item.examples.length > 0 ? (
            item.examples.map((example, i) => (
              <div key={i} className="lesson-example">
                <p>{example.japanese_sentence}</p>
                <p className="lesson-kana">{example.kana_sentence}</p>
                <p>{example.english_translation}</p>
              </div>
            ))
          ) : (
            <p>No examples yet.</p>
          ))}

        {activeTab === 'Notes' &&
          (item.notes.note_text || item.notes.mnemonic_text ? (
            <div>
              {item.notes.note_text && <p>Note: {item.notes.note_text}</p>}
              {item.notes.mnemonic_text && <p>Mnemonic: {item.notes.mnemonic_text}</p>}
            </div>
          ) : (
            <p>No notes yet.</p>
          ))}

        {activeTab === 'Similar' &&
          (item.similar_items.length > 0 ? <p>{item.similar_items.join('; ')}</p> : <p>No similar items listed.</p>)}
      </div>
    </div>
  )
}

export default ItemInfoPanel
