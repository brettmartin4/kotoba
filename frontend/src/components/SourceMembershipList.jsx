function SourceMembershipList({ sources }) {
  if (sources.length === 0) {
    return <p>No source memberships.</p>
  }

  return (
    <ul className="membership-list">
      {sources.map((s) => (
        <li key={s.source_id}>
          {s.display_name} — Level {s.source_level}, position {s.level_position}
          {!s.is_active && ' (inactive)'}
          {s.source_note && <span className="source-note"> — "{s.source_note}"</span>}
        </li>
      ))}
    </ul>
  )
}

export default SourceMembershipList
