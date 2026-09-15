import { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'

function App() {
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    // Fetch dummy data from FastAPI backend
    axios.get('http://127.0.0.1:8000/api/test')
      .then(response => {
        setMessage(response.data.message)
        setLoading(false)
      })
      .catch(error => {
        console.error('Error connecting to backend:', error)
        setError('Failed to connect to backend')
        setLoading(false)
      })
  }, [])

  return (
    <div className="App" style={{ padding: '2rem', textAlign: 'center', fontFamily: 'sans-serif' }}>
      <h1>Video-to-Clips App</h1>
      <div style={{
        marginTop: '2rem',
        padding: '2rem',
        borderRadius: '8px',
        backgroundColor: '#1a1a1a',
        color: '#fff',
        display: 'inline-block'
      }}>
        <h2>Backend Connection Status:</h2>
        {loading && <p>Connecting to backend...</p>}
        {error && <p style={{ color: '#ff6b6b' }}>{error}</p>}
        {message && <p style={{ color: '#51cf66', fontWeight: 'bold' }}>✅ {message}</p>}
      </div>
    </div>
  )
}

export default App
