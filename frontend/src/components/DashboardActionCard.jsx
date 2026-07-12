function DashboardActionCard({ variant, glyph, title, count, buttonLabel, onClick, disabled }) {
  return (
    <div className={`dashboard-action-card action-card-${variant}`}>
      <span className="action-card-glyph" aria-hidden="true">
        {glyph}
      </span>
      <p className="action-card-title">
        {title}
        <span className="action-card-count">{count}</span>
      </p>
      <button type="button" className="action-card-button" onClick={onClick} disabled={disabled}>
        {buttonLabel}
      </button>
    </div>
  )
}

export default DashboardActionCard
