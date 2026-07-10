async function parseErrorMessage(response, fallback) {
  try {
    const body = await response.json()
    return body.detail || fallback
  } catch {
    return fallback
  }
}

export async function fetchReviewsAvailable() {
  const response = await fetch('/api/reviews/available')
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Reviews available request failed: ${response.status}`))
  }
  return response.json()
}

export async function startReview() {
  const response = await fetch('/api/reviews/start', { method: 'POST' })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Start review failed: ${response.status}`))
  }
  return response.json()
}

export async function submitReviewAnswer(sessionId, itemId, promptType, submittedAnswer) {
  const response = await fetch(`/api/reviews/${sessionId}/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ item_id: itemId, prompt_type: promptType, submitted_answer: submittedAnswer }),
  })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Answer submission failed: ${response.status}`))
  }
  return response.json()
}

export async function completeReview(sessionId) {
  const response = await fetch(`/api/reviews/${sessionId}/complete`, { method: 'POST' })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Complete review failed: ${response.status}`))
  }
  return response.json()
}
