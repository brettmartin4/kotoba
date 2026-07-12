function ReviewForecast({ forecast }) {
  const maxNewItems = Math.max(...forecast.rows.map((row) => row.new_items), 0)

  return (
    <div className="review-forecast-card">
      <div className="review-forecast-header">
        <p className="review-forecast-header-label">{forecast.header_label}</p>
        <p className="review-forecast-header-count">+{forecast.header_new_items} items</p>
      </div>
      <div className="review-forecast-body">
        {forecast.rows.map((row) => {
          const barWidth = maxNewItems > 0 ? (row.new_items / maxNewItems) * 100 : 0
          return (
            <div key={row.end_at} className="review-forecast-row">
              <span className="review-forecast-day">{row.label}</span>
              <div className="review-forecast-bar-track">
                <div className="review-forecast-bar-fill" style={{ width: `${barWidth}%` }} />
              </div>
              <span className="review-forecast-count">
                (+{row.new_items}) {row.cumulative_available}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default ReviewForecast
