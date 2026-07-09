export async function fetchDashboard() {
  const response = await fetch('/api/dashboard')
  if (!response.ok) {
    throw new Error(`Dashboard request failed: ${response.status}`)
  }
  return response.json()
}
