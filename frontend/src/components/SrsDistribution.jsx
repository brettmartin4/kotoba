const BUCKETS = [
  { label: 'Unstarted', stages: [0] },
  { label: 'Apprentice', stages: [1, 2, 3, 4] },
  { label: 'Guru', stages: [5, 6] },
  { label: 'Master', stages: [7] },
  { label: 'Enlightened', stages: [8] },
  { label: 'Burned', stages: [9] },
]

function SrsDistribution({ distribution }) {
  return (
    <ul className="srs-distribution">
      {BUCKETS.map((bucket) => {
        const count = bucket.stages.reduce((sum, stage) => sum + (distribution[String(stage)] || 0), 0)
        return (
          <li key={bucket.label}>
            <span className="srs-bucket-count">{count}</span>
            <span className="srs-bucket-label">{bucket.label}</span>
          </li>
        )
      })}
    </ul>
  )
}

export default SrsDistribution
