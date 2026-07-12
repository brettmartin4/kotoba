import { ClockIcon, EyeIcon } from './icons'

function UtilityRow({ itemId, revealEnabled, revealed, onToggleReveal }) {
  return (
    <div className="utility-row full-bleed">
      <a
        className="utility-button"
        href={`/items/${itemId}`}
        target="_blank"
        rel="noreferrer"
        aria-label="View item details in a new tab"
      >
        <ClockIcon />
      </a>
      <button
        type="button"
        className={`utility-button ${revealed ? 'active' : ''}`}
        disabled={!revealEnabled}
        onClick={onToggleReveal}
        aria-label="Reveal meaning, reading, examples, and notes"
      >
        <EyeIcon />
      </button>
    </div>
  )
}

export default UtilityRow
