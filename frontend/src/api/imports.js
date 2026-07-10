async function parseErrorMessage(response, fallback) {
  try {
    const body = await response.json()
    return body.detail || fallback
  } catch {
    return fallback
  }
}

export async function triggerImportRefresh() {
  const response = await fetch('/api/import/refresh', { method: 'POST' })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Import refresh failed: ${response.status}`))
  }
  return response.json()
}

export async function fetchImportRuns() {
  const response = await fetch('/api/import/runs')
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Import runs request failed: ${response.status}`))
  }
  return response.json()
}

export async function fetchImportRunDetail(runId) {
  const response = await fetch(`/api/import/runs/${runId}`)
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Import run detail request failed: ${response.status}`))
  }
  return response.json()
}
