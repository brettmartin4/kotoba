export function promptLabel(itemType, promptType) {
  const typeLabel = itemType === 'word' ? 'Word' : 'Phrase'
  const directionLabel = promptType === 'meaning' ? 'Meaning' : 'Japanese'
  return `${typeLabel} ${directionLabel}`
}

// Kana reading shown below the banner text during meaning prompts (where the
// Japanese form is the stimulus). Never shown for the reverse direction --
// that prompt shows the English meaning as the banner text, not kanji, so
// there's nothing to annotate. Also skipped when kana === japanese (kana-only
// items), since displaying the identical text twice is just noise.
export function promptFurigana(item, promptType) {
  if (promptType !== 'meaning') return null
  if (item.kana === item.japanese) return null
  return item.kana
}
