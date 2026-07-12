// Same 6-bucket stage grouping SrsDistribution.jsx uses, reused here rather
// than reinvented, since Item Spread replaces it on the dashboard.
const BUCKETS = [
  { label: 'Unstarted', stages: [0] },
  { label: 'Apprentice', stages: [1, 2, 3, 4] },
  { label: 'Guru', stages: [5, 6] },
  { label: 'Master', stages: [7] },
  { label: 'Enlightened', stages: [8] },
  { label: 'Burned', stages: [9] },
]

function ItemSpreadPanel({ distributionByType }) {
  return (
    <div className="item-spread-panel">
      {BUCKETS.map((bucket) => {
        const wordCount = bucket.stages.reduce(
          (sum, stage) => sum + (distributionByType[String(stage)]?.word || 0),
          0,
        )
        const phraseCount = bucket.stages.reduce(
          (sum, stage) => sum + (distributionByType[String(stage)]?.phrase || 0),
          0,
        )
        const totalCount = wordCount + phraseCount
        return (
          <div key={bucket.label} className="item-spread-row">
            <span className="item-spread-label">{bucket.label}</span>
            <span className="item-spread-badge item-word">{wordCount}</span>
            <span className="item-spread-badge item-phrase">{phraseCount}</span>
            <span className="item-spread-badge item-spread-badge-total">{totalCount}</span>
          </div>
        )
      })}
    </div>
  )
}

export default ItemSpreadPanel
