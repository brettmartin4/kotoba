async function parseErrorMessage(response, fallback) {
  try {
    const body = await response.json()
    return body.detail || fallback
  } catch {
    return fallback
  }
}

export async function fetchSources() {
  const response = await fetch('/api/sources')
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Sources request failed: ${response.status}`))
  }
  return response.json()
}

export async function renameSource(sourceId, displayName) {
  const response = await fetch(`/api/sources/${sourceId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ display_name: displayName }),
  })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Rename source failed: ${response.status}`))
  }
  return response.json()
}
