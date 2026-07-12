import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchItemDetail } from '../api/items'
import NotesEditor from '../components/NotesEditor'
import SourceMembershipList from '../components/SourceMembershipList'
import SynonymEditor from '../components/SynonymEditor'
import './Browse.css'
import './Reviews.css'

function ItemDetail() {
  const { itemId } = useParams()
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState(null)

  const reload = useCallback(() => {
    fetchItemDetail(itemId)
      .then(setDetail)
      .catch((err) => setError(err.message))
  }, [itemId])

  useEffect(() => {
    reload()
  }, [reload])

  if (error) {
    return (
      <main className="item-detail-screen">
        <p className="dashboard-error">{error}</p>
      </main>
    )
  }

  if (!detail) {
    return (
      <main className="item-detail-screen">
        <p>Loading...</p>
      </main>
    )
  }

  return (
    <main className="item-detail-screen">
      <div className={`item-detail-heading item-${detail.item_type}`}>
        <h1>{detail.japanese}</h1>
        <p className="lesson-kana">
          {detail.kana} &middot; {detail.romaji} &middot; {detail.item_type} &middot; {detail.part_of_speech}
        </p>
      </div>

      <section>
        <h2>Meanings</h2>
        <SynonymEditor itemId={detail.item_id} meanings={detail.meanings} onChange={reload} />
      </section>

      <section>
        <h2>SRS Status</h2>
        <div className="field-row">
          <span className="field-label">Stage</span>
          <span className="field-value">{detail.srs.stage_label}</span>
        </div>
        <div className="field-row">
          <span className="field-label">Next review</span>
          <span className="field-value">{detail.srs.next_review_at || 'N/A'}</span>
        </div>
        <div className="field-row">
          <span className="field-label">Accuracy</span>
          <span className="field-value">
            {detail.srs.accuracy_percent !== null ? `${detail.srs.accuracy_percent}%` : 'No reviews yet'}
          </span>
        </div>
        <div className="field-row">
          <span className="field-label">Total reviews</span>
          <span className="field-value">{detail.srs.total_reviews}</span>
        </div>
        <div className="field-row">
          <span className="field-label">Incorrect</span>
          <span className="field-value">{detail.srs.incorrect_reviews}</span>
        </div>
        <div className="field-row">
          <span className="field-label">Current streak</span>
          <span className="field-value">{detail.srs.current_correct_streak}</span>
        </div>
        <div className="field-row">
          <span className="field-label">Longest streak</span>
          <span className="field-value">{detail.srs.longest_correct_streak}</span>
        </div>
      </section>

      <section>
        <h2>Examples</h2>
        {detail.examples.length > 0 ? (
          detail.examples.map((example, i) => (
            <div key={i} className="example-block">
              <p className="example-japanese">{example.japanese_sentence}</p>
              <p className="example-kana">{example.kana_sentence}</p>
              <p className="example-english">{example.english_translation}</p>
            </div>
          ))
        ) : (
          <p>No examples yet.</p>
        )}
      </section>

      <section>
        <h2>Similar Items</h2>
        <p>{detail.similar_items.length > 0 ? detail.similar_items.join('; ') : 'None listed.'}</p>
      </section>

      <section>
        <h2>Source Memberships</h2>
        <SourceMembershipList sources={detail.sources} />
      </section>

      <section>
        <h2>Notes &amp; Mnemonic</h2>
        <NotesEditor itemId={detail.item_id} notes={detail.notes} />
      </section>

      <section>
        <h2>Recent Review History</h2>
        {detail.review_history.length > 0 ? (
          <ul className="history-list">
            {detail.review_history.map((entry, i) => (
              <li key={i}>
                {entry.created_at} — {entry.prompt_type} — {entry.is_correct ? 'correct' : 'incorrect'}
              </li>
            ))}
          </ul>
        ) : (
          <p>No review history yet.</p>
        )}
      </section>
    </main>
  )
}

export default ItemDetail
