function StudyBanner({ itemType, display, label }) {
  return (
    <div className={`study-banner full-bleed item-${itemType}`}>
      <div className="study-banner-display">
        <h1>{display}</h1>
      </div>
      <div className="study-banner-label">{label}</div>
    </div>
  )
}

export default StudyBanner
