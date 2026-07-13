async function parseErrorMessage(response, fallback) {
  try {
    const body = await response.json()
    return body.detail || fallback
  } catch {
    return fallback
  }
}

export async function fetchSettings() {
  const response = await fetch('/api/settings')
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Settings request failed: ${response.status}`))
  }
  return response.json()
}

export async function updateDailyLessonCap(dailyLessonCap) {
  const response = await fetch('/api/settings', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ daily_lesson_cap: dailyLessonCap }),
  })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, `Update settings failed: ${response.status}`))
  }
  return response.json()
}
