async function parseErrorMessage(response, fallback) {
  try {
    const body = await response.json()
    return body.detail || fallback
  } catch {
    return fallback
  }
}

export async function fetchLessonsAvailable() {
  const response = await fetch('/api/lessons/available')
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Lessons available request failed: ${response.status}`))
  }
  return response.json()
}

export async function startLesson(sourceId) {
  const response = await fetch('/api/lessons/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_id: sourceId }),
  })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Start lesson failed: ${response.status}`))
  }
  return response.json()
}

export async function submitLessonAnswer(sessionId, itemId, promptType, submittedAnswer) {
  const response = await fetch(`/api/lessons/${sessionId}/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ item_id: itemId, prompt_type: promptType, submitted_answer: submittedAnswer }),
  })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Answer submission failed: ${response.status}`))
  }
  return response.json()
}

export async function completeLesson(sessionId) {
  const response = await fetch(`/api/lessons/${sessionId}/complete`, { method: 'POST' })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Complete lesson failed: ${response.status}`))
  }
  return response.json()
}
