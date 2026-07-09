import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then(setHealth)
      .catch((err) => setError(err.message))
  }, [])

  return (
    <main>
      <h1>KotobaForge</h1>
      <p>Phase 0 scaffold placeholder.</p>
      {health && <p>Backend status: {health.status} (db: {health.db})</p>}
      {error && <p>Backend unreachable: {error}</p>}
    </main>
  )
}

export default App
