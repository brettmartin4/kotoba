function StudyBanner({ itemType, display, label, furigana }) {
  return (
    <div className={`study-banner full-bleed item-${itemType}`}>
      <div className="study-banner-display">
        <h1>{display}</h1>
        {furigana && <p className="study-banner-furigana">{furigana}</p>}
      </div>
      <div className="study-banner-label">{label}</div>
    </div>
  )
}

export default StudyBanner
