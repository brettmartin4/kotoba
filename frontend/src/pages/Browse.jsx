import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchItems } from '../api/items'
import { fetchSources } from '../api/sources'
import './Browse.css'

const SRS_GROUPS = ['all', 'unstarted', 'apprentice', 'guru', 'master', 'enlightened', 'burned']

function Browse() {
  const [search, setSearch] = useState('')
  const [sourceId, setSourceId] = useState('')
  const [itemType, setItemType] = useState('')
  const [srsGroup, setSrsGroup] = useState('all')
  const [activeFilter, setActiveFilter] = useState('active_only')
  const [sources, setSources] = useState([])
  const [items, setItems] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchSources()
      .then(setSources)
      .catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    setError(null)
    const timeout = setTimeout(() => {
      fetchItems({
        search: search || undefined,
        source_id: sourceId || undefined,
        item_type: itemType || undefined,
        srs_group: srsGroup,
        active_filter: activeFilter,
      })
        .then(setItems)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false))
    }, 250)
    return () => clearTimeout(timeout)
  }, [search, sourceId, itemType, srsGroup, activeFilter])

  return (
    <main className="browse-screen">
      <h1>Browse</h1>

      <div className="browse-filters">
        <input
          type="text"
          placeholder="Search japanese, kana, meanings, notes..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
          <option value="">All sources</option>
          {sources.map((source) => (
            <option key={source.id} value={source.id}>
              {source.display_name}
            </option>
          ))}
        </select>
        <select value={itemType} onChange={(e) => setItemType(e.target.value)}>
          <option value="">Word + Phrase</option>
          <option value="word">Word</option>
          <option value="phrase">Phrase</option>
        </select>
        <select value={srsGroup} onChange={(e) => setSrsGroup(e.target.value)}>
          {SRS_GROUPS.map((group) => (
            <option key={group} value={group}>
              {group === 'all' ? 'All SRS stages' : group}
            </option>
          ))}
        </select>
        <select value={activeFilter} onChange={(e) => setActiveFilter(e.target.value)}>
          <option value="active_only">Active only</option>
          <option value="all">Active + inactive</option>
          <option value="inactive_only">Inactive only</option>
        </select>
      </div>

      {error && <p className="dashboard-error">{error}</p>}
      {loading && <p>Loading...</p>}

      {!loading && !error && (
        <table className="browse-table">
          <thead>
            <tr>
              <th>Japanese</th>
              <th>Kana</th>
              <th>Meanings</th>
              <th>Type</th>
              <th>SRS Stage</th>
              <th>Sources</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.item_id}>
                <td>
                  <Link to={`/items/${item.item_id}`}>{item.japanese}</Link>
                </td>
                <td>{item.kana}</td>
                <td>{item.meanings.join('; ')}</td>
                <td>{item.item_type}</td>
                <td>{item.srs_stage_label}</td>
                <td>{item.sources.map((s) => `${s.display_name}${s.is_active ? '' : ' (inactive)'}`).join(', ')}</td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={6}>No items match these filters.</td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </main>
  )
}

export default Browse
