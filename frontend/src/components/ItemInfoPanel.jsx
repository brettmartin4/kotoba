import { useState } from 'react'
import '../pages/Reviews.css'

const TABS = ['Meaning', 'Reading', 'Examples', 'Notes', 'Similar']

function ItemInfoPanel({ item }) {
  const [activeTab, setActiveTab] = useState('Meaning')

  return (
    <div className={`item-info-panel item-${item.item_type}`}>
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
            <ul className="meaning-list">
              {item.meanings.map((meaning, i) => (
                <li key={i}>{meaning}</li>
              ))}
            </ul>
            <div className="field-row">
              <span className="field-label">Part of speech</span>
              <span className="field-value">{item.part_of_speech}</span>
            </div>
          </div>
        )}

        {activeTab === 'Reading' && (
          <div>
            <div className="field-row">
              <span className="field-label">Japanese</span>
              <span className="field-value">{item.japanese}</span>
            </div>
            <div className="field-row">
              <span className="field-label">Kana</span>
              <span className="field-value">{item.kana}</span>
            </div>
            <div className="field-row">
              <span className="field-label">Romaji</span>
              <span className="field-value">{item.romaji}</span>
            </div>
          </div>
        )}

        {activeTab === 'Examples' &&
          (item.examples.length > 0 ? (
            item.examples.map((example, i) => (
              <div key={i} className="example-block">
                <p className="example-japanese">{example.japanese_sentence}</p>
                <p className="example-kana">{example.kana_sentence}</p>
                <p className="example-english">{example.english_translation}</p>
              </div>
            ))
          ) : (
            <p>No examples yet.</p>
          ))}

        {activeTab === 'Notes' &&
          (item.notes.note_text || item.notes.mnemonic_text ? (
            <div>
              {item.notes.note_text && (
                <div className="note-block">
                  <span className="field-label">Note</span>
                  <p>{item.notes.note_text}</p>
                </div>
              )}
              {item.notes.mnemonic_text && (
                <div className="note-block">
                  <span className="field-label">Mnemonic</span>
                  <p>{item.notes.mnemonic_text}</p>
                </div>
              )}
            </div>
          ) : (
            <p>No notes yet.</p>
          ))}

        {activeTab === 'Similar' &&
          (item.similar_items.length > 0 ? (
            <ul className="meaning-list">
              {item.similar_items.map((similar, i) => (
                <li key={i}>{similar}</li>
              ))}
            </ul>
          ) : (
            <p>No similar items listed.</p>
          ))}
      </div>
    </div>
  )
}

export default ItemInfoPanel
