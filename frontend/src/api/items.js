async function parseErrorMessage(response, fallback) {
  try {
    const body = await response.json()
    return body.detail || fallback
  } catch {
    return fallback
  }
}

export async function fetchItems(params = {}) {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, value)
    }
  }
  const response = await fetch(`/api/items?${query.toString()}`)
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Items request failed: ${response.status}`))
  }
  return response.json()
}

export async function fetchItemDetail(itemId) {
  const response = await fetch(`/api/items/${itemId}`)
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Item detail request failed: ${response.status}`))
  }
  return response.json()
}

export async function updateItemNotes(itemId, updates) {
  const response = await fetch(`/api/items/${itemId}/notes`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Notes update failed: ${response.status}`))
  }
  return response.json()
}

export async function addSynonym(itemId, meaning) {
  const response = await fetch(`/api/items/${itemId}/synonyms`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ meaning }),
  })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Add synonym failed: ${response.status}`))
  }
  return response.json()
}

export async function deleteSynonym(itemId, synonymId) {
  const response = await fetch(`/api/items/${itemId}/synonyms/${synonymId}`, { method: 'DELETE' })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Delete synonym failed: ${response.status}`))
  }
  return response.json()
}
