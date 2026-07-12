const EMPTY_STATS = { active_item_count: 0, guru_or_higher_count: 0, percent_guru: 0 }

function ProgressBarRow({ itemType, icon, stats }) {
  return (
    <div className={`level-progress-bar-row item-${itemType}`}>
      <span className="level-progress-icon">{icon}</span>
      <div className="level-progress-bar-track">
        <div className="level-progress-bar-fill" style={{ width: `${stats.percent_guru}%` }} />
      </div>
      <span className="level-progress-bar-count">
        {stats.guru_or_higher_count}/{stats.active_item_count} Guru+
      </span>
    </div>
  )
}

function LevelProgressPanel({ source }) {
  // The current level can be newly unlocked with no items assigned to it
  // yet, so there may be no matching entry in source.levels at all.
  const currentLevelData = source.levels.find((l) => l.level === source.current_level)
  const byType = currentLevelData?.by_type || { word: EMPTY_STATS, phrase: EMPTY_STATS }

  return (
    <div className="level-progress-panel">
      <div className="level-progress-header">
        <h3>{source.display_name}</h3>
        <span className="level-progress-level">
          {source.current_level > 0 ? `Level ${source.current_level}` : 'No items yet'}
        </span>
      </div>
      <ProgressBarRow itemType="word" icon="A" stats={byType.word} />
      <ProgressBarRow itemType="phrase" icon="あ" stats={byType.phrase} />
    </div>
  )
}

export default LevelProgressPanel
