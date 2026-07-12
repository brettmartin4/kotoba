export function promptLabel(itemType, promptType) {
  const typeLabel = itemType === 'word' ? 'Word' : 'Phrase'
  const directionLabel = promptType === 'meaning' ? 'Meaning' : 'Japanese'
  return `${typeLabel} ${directionLabel}`
}
