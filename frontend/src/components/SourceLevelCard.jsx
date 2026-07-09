function SourceLevelCard({ source }) {
  return (
    <div className="source-card">
      <h3>{source.display_name}</h3>
      <p className="source-level">
        {source.current_level > 0 ? `Level ${source.current_level}` : 'No items yet'}
      </p>
      <p>
        {source.lessons_available_in_source} lesson{source.lessons_available_in_source === 1 ? '' : 's'} available
      </p>
      {source.levels.length > 0 && (
        <ul className="level-list">
          {source.levels.map((level) => (
            <li key={level.level} className={level.is_unlocked ? 'unlocked' : 'locked'}>
              Level {level.level}: {level.guru_or_higher_count}/{level.active_item_count} Guru+ ({level.percent_guru}%)
              {!level.is_unlocked && ' — locked'}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default SourceLevelCard
