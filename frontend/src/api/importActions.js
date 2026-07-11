async function parseErrorMessage(response, fallback) {
  try {
    const body = await response.json()
    return body.detail || fallback
  } catch {
    return fallback
  }
}

export async function fetchPendingDuplicates() {
  const response = await fetch('/api/import/duplicates/pending')
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Pending duplicates request failed: ${response.status}`))
  }
  return response.json()
}

export async function fetchPendingChanges() {
  const response = await fetch('/api/import/changes/pending')
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Pending changes request failed: ${response.status}`))
  }
  return response.json()
}

export async function mergeDuplicate(importRunItemId, targetItemId) {
  const response = await fetch(`/api/import/duplicates/${importRunItemId}/merge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_item_id: targetItemId }),
  })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Merge failed: ${response.status}`))
  }
  return response.json()
}

export async function keepDuplicateSeparate(importRunItemId) {
  const response = await fetch(`/api/import/duplicates/${importRunItemId}/keep-separate`, { method: 'POST' })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Keep separate failed: ${response.status}`))
  }
  return response.json()
}

export async function skipDuplicate(importRunItemId) {
  const response = await fetch(`/api/import/duplicates/${importRunItemId}/skip`, { method: 'POST' })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Skip failed: ${response.status}`))
  }
  return response.json()
}

export async function approveChange(importRunItemId) {
  const response = await fetch(`/api/import/changes/${importRunItemId}/approve`, { method: 'POST' })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Approve failed: ${response.status}`))
  }
  return response.json()
}

export async function rejectChange(importRunItemId) {
  const response = await fetch(`/api/import/changes/${importRunItemId}/reject`, { method: 'POST' })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Reject failed: ${response.status}`))
  }
  return response.json()
}
